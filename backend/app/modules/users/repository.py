"""
User repository — all DB operations for the users module.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import RefreshToken, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        bar_council_id: str | None = None,
        phone: str | None = None,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
            bar_council_id=bar_council_id,
            phone=phone,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(tz=timezone.utc))
        )

    async def update_profile(
        self,
        user_id: uuid.UUID,
        full_name: str | None = None,
        bar_council_id: str | None = None,
        phone: str | None = None,
    ) -> User | None:
        values: dict = {}
        if full_name is not None:
            values["full_name"] = full_name
        if bar_council_id is not None:
            values["bar_council_id"] = bar_council_id
        if phone is not None:
            values["phone"] = phone
        if values:
            await self.session.execute(
                update(User).where(User.id == user_id).values(**values)
            )
        return await self.get_by_id(user_id)

    async def update_password_hash(self, user_id: uuid.UUID, new_hash: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(password_hash=new_hash)
        )

    # ── Refresh tokens ─────────────────────────────────────────────────────────

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(rt)
        await self.session.flush()
        return rt

    async def get_refresh_token(self, raw_token: str) -> RefreshToken | None:
        token_hash = self._hash_token(raw_token)
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, raw_token: str) -> None:
        token_hash = self._hash_token(raw_token)
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True, revoked_at=datetime.now(tz=timezone.utc))
        )

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
            .values(revoked=True, revoked_at=datetime.now(tz=timezone.utc))
        )