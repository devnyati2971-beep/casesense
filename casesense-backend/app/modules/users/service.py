"""
User service — business logic for auth, profile, and the v2.1 auth lifecycle
(email verification, password recovery/change, refresh-token rotation).
"""

from __future__ import annotations

import secrets
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
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.emails.service import EmailService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import TokenPair, UserRegisterRequest

_AUTH_TOKEN_TTL = timedelta(hours=settings.VERIFICATION_TOKEN_TTL_HOURS)
_EMAIL_OTP_TTL = timedelta(minutes=settings.EMAIL_VERIFICATION_OTP_TTL_MINUTES)
_RESET_TOKEN_TTL = timedelta(minutes=settings.RESET_TOKEN_TTL_MINUTES)


def _validate_password_strength(password: str) -> None:
    """Apply the same password policy to registration, reset, and change."""
    if len(password) < 8 or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
        raise ValidationError(
            "Password must be at least 8 characters and include an uppercase letter and a digit.",
            code="WEAK_PASSWORD",
        )


class UserService:
    def __init__(self, session: AsyncSession, background_tasks: "fastapi.BackgroundTasks | None" = None) -> None:
        self.session = session
        self.background_tasks = background_tasks
        self.repo = UserRepository(session)

    # ── Registration / login ───────────────────────────────────────────────────

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
        await self.session.commit()

        # Queue the verification email (§14.2) — token bound to the user, not client claims.
        await self._queue_verification(user, ip_address)
        await self.session.commit()
        return user, tokens

    async def login(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, TokenPair]:
        user = await self.repo.get_by_email(email)
        if user is None or user.password_hash is None:
            # Generic error — never reveal which field is wrong (§16).
            raise InvalidCredentialsError()

        verify_password(password, user.password_hash)

        if not user.is_verified:
            await self._queue_verification(user, ip_address)
            await self.session.commit()
            raise ValidationError(
                "Email not verified. A new verification email has been sent.", 
                code="EMAIL_NOT_VERIFIED",
                background_tasks=self.background_tasks
            )

        if password_needs_rehash(user.password_hash):
            new_hash = hash_password(password)
            await self.repo.update_password_hash(user.id, new_hash)

        await self.repo.update_last_login(user.id)
        tokens = await self._issue_tokens(user, user_agent, ip_address)
        await self.session.commit()
        return user, tokens

    async def refresh_tokens(
        self,
        raw_refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        payload = decode_refresh_token(raw_refresh_token)  # raises on bad/expired

        stored = await self.repo.get_refresh_token_including_revoked(raw_refresh_token)
        if stored is None:
            raise TokenInvalidError()

        now = datetime.now(tz=timezone.utc)
        if stored.revoked:
            # Reuse of a rotated token ⇒ theft signal ⇒ revoke the whole family (§14).
            if stored.family_id:
                await self.repo.revoke_family(stored.family_id)
            await self.session.commit()
            raise TokenInvalidError()

        if stored.expires_at.replace(tzinfo=timezone.utc) < now:
            raise TokenExpiredError()

        user_id = uuid.UUID(payload["sub"])
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError()

        # Rotate: revoke old, issue new within the same family (one txn).
        await self.repo.revoke_refresh_token(raw_refresh_token)
        tokens = await self._issue_tokens(user, user_agent, ip_address, family_id=stored.family_id)
        await self.session.commit()
        return tokens

    async def logout(self, raw_refresh_token: str) -> None:
        await self.repo.revoke_refresh_token(raw_refresh_token)
        await self.session.commit()

    async def logout_all(self, user_id: uuid.UUID, raw_refresh_token: str | None = None) -> None:
        """Revoke all of the user's refresh families except the caller's current one (§14.5)."""
        caller_family = None
        if raw_refresh_token:
            stored = await self.repo.get_refresh_token_including_revoked(raw_refresh_token)
            if stored and not stored.revoked:
                caller_family = stored.family_id
        if caller_family:
            await self.repo.revoke_all_except_family(user_id, caller_family)
        else:
            await self.repo.revoke_all_user_tokens(user_id)
        await self.session.commit()

    # ── Email verification (v2.1 §14.2) ───────────────────────────────────────

    async def _queue_verification(self, user: User, ip_address: str | None) -> None:
        await self.repo.invalidate_auth_tokens(user.id, "EMAIL_VERIFICATION")
        code = f"{secrets.randbelow(1_000_000):06d}"
        # Scope the stored hash to the user so identical six-digit codes can
        # safely exist for different accounts despite the global unique hash.
        stored_token = f"{user.id}:{code}"
        await self.repo.store_auth_token(
            user.id, "EMAIL_VERIFICATION", stored_token,
            expires_at=datetime.now(tz=timezone.utc) + _EMAIL_OTP_TTL,
            requested_ip=ip_address,
        )
        await EmailService.send(
            db=self.session,
            to_email=user.email,
            template="verify_email",
            params={"code": code},
            user_id=user.id,
            related_resource_type="USER",
            related_resource_id=str(user.id),
            background_tasks=self.background_tasks,
        )

    async def verify_email(self, user_id: uuid.UUID, code: str) -> bool:
        token = await self.repo.get_auth_token("EMAIL_VERIFICATION", f"{user_id}:{code}")
        now = datetime.now(tz=timezone.utc)
        if token is None or token.used_at is not None:
            raise ValidationError("INVALID_TOKEN", code="INVALID_TOKEN")
        if token.expires_at.replace(tzinfo=timezone.utc) < now:
            raise ValidationError("INVALID_TOKEN", code="INVALID_TOKEN")

        await self.repo.mark_auth_token_used(token.id)
        await self.repo.set_email_verified(user_id)
        await self.session.commit()
        return True

    async def resend_verification(self, email: str) -> None:
        """Always 204 — no account-existence disclosure (§14.2, §16)."""
        user = await self.repo.get_by_email(email)
        if user and not user.is_verified:
            await self._queue_verification(user, None)
            await self.session.commit()

    # ── Password recovery (v2.1 §14.3) ────────────────────────────────────────

    async def forgot_password(self, email: str) -> None:
        """Always 204 — no account-existence disclosure (§14.3)."""
        user = await self.repo.get_by_email(email)
        if user is None:
            return
        if user.password_hash is None:
            # OAuth-only account: security notice, no reset token.
            await EmailService.send(
                db=self.session, to_email=user.email, template="security_notice", user_id=user.id,
                background_tasks=self.background_tasks,
            )
            await self.session.commit()
            return

        await self.repo.invalidate_auth_tokens(user.id, "PASSWORD_RESET")
        raw_token = secrets.token_urlsafe(32)
        await self.repo.store_auth_token(
            user.id, "PASSWORD_RESET", raw_token,
            expires_at=datetime.now(tz=timezone.utc) + _RESET_TOKEN_TTL,
        )
        link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={raw_token}"
        await EmailService.send(
            db=self.session, to_email=user.email, template="reset_password",
            params={"link": link}, user_id=user.id,
            background_tasks=self.background_tasks,
        )
        await self.session.commit()

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        _validate_password_strength(new_password)

        token = await self.repo.get_auth_token("PASSWORD_RESET", raw_token)
        now = datetime.now(tz=timezone.utc)
        if token is None:
            raise ValidationError("INVALID_TOKEN", code="INVALID_TOKEN")
        if token.used_at is not None or token.expires_at.replace(tzinfo=timezone.utc) < now:
            # Reuse of a consumed token re-queues a security notice (§14.3).
            if token.used_at is not None:
                user = await self.repo.get_by_id(token.user_id)
                if user:
                    await EmailService.send(
                        db=self.session, to_email=user.email, template="security_notice", user_id=user.id,
                        background_tasks=self.background_tasks,
                    )
                    await self.session.commit()
            raise ValidationError("INVALID_TOKEN", code="INVALID_TOKEN")

        await self.repo.mark_auth_token_used(token.id)
        await self.repo.update_password(token.user_id, hash_password(new_password))
        # Revoke ALL refresh families (stolen-session defence).
        await self.repo.revoke_all_user_tokens(token.user_id)
        await EmailService.send(
            db=self.session,
            to_email=(await self.repo.get_by_id(token.user_id)).email,
            template="security_notice",
            user_id=token.user_id,
            background_tasks=self.background_tasks,
        )
        await self.session.commit()

    # ── Change password (v2.1 §14.4) ──────────────────────────────────────────

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str | None,
        new_password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, TokenPair | None]:
        _validate_password_strength(new_password)

        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))

        # OAuth-only account may set a password with current_password omitted (§14.6).
        if user.password_hash is not None:
            if not current_password:
                raise InvalidCredentialsError()
            verify_password(current_password, user.password_hash)
        elif current_password is not None:
            raise InvalidCredentialsError()

        await self.repo.update_password(user.id, hash_password(new_password))

        # Keep the caller's session on a fresh family; revoke the rest (§14.7).
        new_family = uuid.uuid4()
        await self.repo.revoke_all_user_tokens(user.id)
        tokens = await self._issue_tokens(user, user_agent, ip_address, family_id=new_family)

        await EmailService.send(
            db=self.session, to_email=user.email, template="password_changed", user_id=user.id,
            background_tasks=self.background_tasks,
        )
        await self.session.commit()
        return user, tokens

    # ── Profile ────────────────────────────────────────────────────────────────

    async def get_me(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        return user

    async def get_profile(self, user_id: uuid.UUID) -> User:
        return await self.get_me(user_id)

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
        await self.session.commit()
        return user

    # ── Internal ───────────────────────────────────────────────────────────────

    async def _issue_tokens(
        self,
        user: User,
        user_agent: str | None,
        ip_address: str | None,
        family_id: uuid.UUID | None = None,
    ) -> TokenPair:
        access = create_access_token(str(user.id), user.role)
        refresh = create_refresh_token(str(user.id))

        family_id = family_id or uuid.uuid4()
        expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.repo.store_refresh_token(
            user.id, refresh, expires_at, user_agent, ip_address,
            family_id=family_id,
        )

        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
