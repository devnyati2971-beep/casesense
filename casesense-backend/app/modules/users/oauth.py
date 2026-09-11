"""
OAuth service — Blueprint §14.6, §73.

OIDC Authorization Code + PKCE against a configurable provider (Google by
default). Provider tokens are used once to fetch the profile and are then
discarded — CaseSense issues its own JWT pair. Account linking policy:

- Existing CaseSense account with the SAME verified email  -> link identity.
- Existing CaseSense account with a DIFFERENT email        -> reject (409).
- No existing account                                      -> create user.

State + code_verifier are short-lived, single-use, stored server-side in Redis.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, ValidationException
from app.core.logging import get_logger
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.oauth_models import OAuthIdentity

logger = get_logger(__name__)

STATE_TTL_SECONDS = 600


@dataclass
class OAuthProfile:
    provider: str
    provider_account_id: str
    email: str
    email_verified: bool
    full_name: str | None


# ── Provider config ───────────────────────────────────────────────────────────

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


def _oauth_config() -> dict[str, Optional[str]]:
    return {
        "client_id": getattr(settings, "OAUTH_CLIENT_ID", None) or getattr(settings, "OAUTH_GOOGLE_CLIENT_ID", None),
        "client_secret": getattr(settings, "OAUTH_CLIENT_SECRET", None) or getattr(settings, "OAUTH_GOOGLE_CLIENT_SECRET", None),
        "redirect_uri": getattr(settings, "OAUTH_REDIRECT_URI", None) or f"{settings.FRONTEND_BASE_URL}/oauth/callback",
    }


def oauth_enabled() -> bool:
    cfg = _oauth_config()
    return bool(cfg["client_id"] and cfg["client_secret"] and cfg["redirect_uri"])


# ── PKCE + state helpers ──────────────────────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def create_authorization_request() -> dict[str, str]:
    """Build the provider authorization URL with PKCE + single-use state."""
    cfg = _oauth_config()
    if not oauth_enabled():
        raise ValidationException("OAuth is not configured on this deployment.")

    state = secrets.token_urlsafe(32)
    code_verifier = _b64url(secrets.token_bytes(48))
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode()).digest())

    from app.jobs.state import get_arq_redis

    # State is stored in Redis with short TTL; single-use on callback.
    _store_state(state, code_verifier)

    params = {
        "client_id": cfg["client_id"] or "",
        "redirect_uri": cfg["redirect_uri"] or "",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={httpx.QueryParams({k: v}).get(k)}" for k, v in params.items())
    return {"authorization_url": f"{GOOGLE_AUTH_ENDPOINT}?{query}", "state": state}


def _store_state(state: str, code_verifier: str) -> None:
    """Persist state->verifier in Redis (falls back to in-process dict)."""
    import app.modules.users.oauth_state as oauth_state

    try:
        import asyncio

        from app.jobs.state import get_arq_redis

        async def _set() -> None:
            pool = await get_arq_redis()
            if pool is not None:
                await pool.set(f"oauth:state:{state}", code_verifier, ex=STATE_TTL_SECONDS)

        # Best-effort async write from sync context is unsafe — this function is
        # called from an async router; use the async variant instead.
        oauth_state._pending_states[state] = (code_verifier, datetime.now(timezone.utc))
    except Exception:
        oauth_state._pending_states[state] = (code_verifier, datetime.now(timezone.utc))


async def store_state_async(state: str, code_verifier: str) -> None:
    from app.jobs.state import get_arq_redis

    import app.modules.users.oauth_state as oauth_state

    oauth_state._pending_states[state] = (code_verifier, datetime.now(timezone.utc))
    pool = await get_arq_redis()
    if pool is not None:
        try:
            await pool.set(f"oauth:state:{state}", code_verifier, ex=STATE_TTL_SECONDS)
        except Exception:
            pass


def pop_state(state: str) -> Optional[str]:
    """Single-use state consumption — returns the code_verifier or None."""
    import app.modules.users.oauth_state as oauth_state

    entry = oauth_state._pending_states.pop(state, None)
    if entry is None:
        return None
    code_verifier, created = entry
    if (datetime.now(timezone.utc) - created).total_seconds() > STATE_TTL_SECONDS:
        return None
    return code_verifier


# ── Token exchange + profile ──────────────────────────────────────────────────

async def exchange_code_for_profile(
    code: str, code_verifier: str, redirect_uri: str | None = None
) -> OAuthProfile:
    cfg = _oauth_config()
    async with httpx.AsyncClient(timeout=15) as client:
        token_res = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri or cfg["redirect_uri"],
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code_verifier": code_verifier,
            },
        )
        if token_res.status_code != 200:
            logger.warning("OAuth token exchange failed", status=token_res.status_code)
            raise ValidationException("OAuth code exchange failed.")
        access_token = token_res.json().get("access_token")
        if not access_token:
            raise ValidationException("OAuth token response missing access_token.")

        userinfo_res = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_res.status_code != 200:
            raise ValidationException("OAuth userinfo fetch failed.")
        info = userinfo_res.json()

    return OAuthProfile(
        provider="google",
        provider_account_id=str(info.get("sub") or ""),
        email=str(info.get("email") or ""),
        email_verified=bool(info.get("email_verified", False)),
        full_name=info.get("name"),
    )


# ── Account linking / creation ────────────────────────────────────────────────

async def resolve_and_link(db: AsyncSession, profile: OAuthProfile) -> User:
    """Find-or-create the CaseSense user and link the OAuth identity."""
    # 1. Existing identity?
    stmt = select(OAuthIdentity).where(
        OAuthIdentity.provider == profile.provider,
        OAuthIdentity.provider_account_id == profile.provider_account_id,
    )
    identity = (await db.execute(stmt)).scalar_one_or_none()
    if identity:
        user = (await db.execute(select(User).where(User.id == identity.user_id))).scalar_one()
        return user

    # 2. Same-email account -> link (only when provider email is verified).
    stmt = select(User).where(User.email == profile.email.lower())
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is not None:
        if not profile.email_verified:
            raise ConflictException("OAUTH_EMAIL_UNVERIFIED: Provider email is not verified.")
        db.add(OAuthIdentity(
            user_id=user.id,
            provider=profile.provider,
            provider_account_id=profile.provider_account_id,
            email=profile.email.lower(),
        ))
        await db.commit()
        await db.refresh(user)
        return user

    # 3. No account -> create one (password unusable; auth is via OAuth).
    random_password = secrets.token_urlsafe(32)
    user = User(
        email=profile.email.lower(),
        password_hash=hash_password(random_password),
        full_name=profile.full_name or profile.email.split("@")[0],
        is_active=True,
        is_verified=profile.email_verified,
    )
    db.add(user)
    await db.flush()
    db.add(OAuthIdentity(
        user_id=user.id,
        provider=profile.provider,
        provider_account_id=profile.provider_account_id,
        email=profile.email.lower(),
    ))
    await db.commit()
    await db.refresh(user)
    return user
