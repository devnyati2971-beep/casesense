"""
User service — business logic for auth and profile.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    NotFoundError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import TokenPair, UserRegisterRequest


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def register(
        self,
        data: UserRegisterRequest,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, TokenPair]:
        existing = await self.repo.get_by_email(data.email)
        if existing:
            raise ConflictError("A user with this email already exists.")

        pw_hash = hash_password(data.password)
        user = await self.repo.create(
            email=data.email,
            password_hash=pw_hash,
            full_name=data.full_name,
            bar_council_id=data.bar_council_id,
            phone=data.phone,
        )
        tokens = await self._issue_tokens(user, user_agent, ip_address)
        return user, tokens

    async def login(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, TokenPair]:
        user = await self.repo.get_by_email(email)
        # Generic error — never reveal which field is wrong
        if user is None:
            raise InvalidCredentialsError()

        verify_password(password, user.password_hash)  # raises on mismatch

        # Opportunistic rehash
        if password_needs_rehash(user.password_hash):
            new_hash = hash_password(password)
            await self.repo.update_password_hash(user.id, new_hash)

        await self.repo.update_last_login(user.id)
        tokens = await self._issue_tokens(user, user_agent, ip_address)
        return user, tokens

    async def refresh_tokens(
        self,
        raw_refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        payload = decode_refresh_token(raw_refresh_token)  # raises on bad/expired

        stored = await self.repo.get_refresh_token(raw_refresh_token)
        if stored is None or stored.revoked:
            raise TokenInvalidError()

        now = datetime.now(tz=timezone.utc)
        if stored.expires_at.replace(tzinfo=timezone.utc) < now:
            raise TokenExpiredError()

        user_id = uuid.UUID(payload["sub"])
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError()

        # Rotate: revoke old, issue new
        await self.repo.revoke_refresh_token(raw_refresh_token)
        return await self._issue_tokens(user, user_agent, ip_address)

    async def logout(self, raw_refresh_token: str) -> None:
        await self.repo.revoke_refresh_token(raw_refresh_token)

    async def get_profile(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def update_profile(
        self,
        user_id: uuid.UUID,
        full_name: str | None = None,
        bar_council_id: str | None = None,
        phone: str | None = None,
    ) -> User:
        user = await self.repo.update_profile(user_id, full_name, bar_council_id, phone)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _issue_tokens(
        self,
        user: User,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        access = create_access_token(str(user.id), user.role)
        refresh = create_refresh_token(str(user.id))

        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.repo.store_refresh_token(
            user.id, refresh, expires_at, user_agent, ip_address
        )

        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )