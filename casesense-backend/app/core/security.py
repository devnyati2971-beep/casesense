"""
Security primitives — password hashing (Argon2) and JWT operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError, TokenExpiredError, TokenInvalidError

# ── Argon2 password hasher ────────────────────────────────────────────────────

_ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
)


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _ph.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    Raises InvalidCredentialsError — never leaks which field is wrong.
    """
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        raise InvalidCredentialsError()


def password_needs_rehash(hashed_password: str) -> bool:
    """Check if password hash needs to be updated (e.g. parameters changed)."""
    return _ph.check_needs_rehash(hashed_password)


# ── JWT ──────────────────────────────────────────────────────────────────────

_TOKEN_TYPE_ACCESS = "access"
_TOKEN_TYPE_REFRESH = "refresh"


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str = "advocate") -> str:
    return _create_token(
        subject=user_id,
        token_type=_TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        subject=user_id,
        token_type=_TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token. Raises on any failure."""
    return _decode_token(token, expected_type=_TOKEN_TYPE_ACCESS)


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token. Raises on any failure."""
    return _decode_token(token, expected_type=_TOKEN_TYPE_REFRESH)


def _decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise TokenInvalidError()

    if payload.get("type") != expected_type:
        raise TokenInvalidError()

    return payload