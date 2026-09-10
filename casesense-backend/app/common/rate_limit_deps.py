"""
FastAPI dependency glue for rate limiting (§75.1) + guest access helpers.

Usage in routers:
    RateLimitDep("auth_login")                       # IP-keyed
    RateLimitDep("ai_translate", keyed_by_user=True) # user-keyed
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.common.rate_limit import check_rate_limit
from app.core.security import decode_access_token

_bearer_opt = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str:
    """Best-effort client IP (behind OCI LB / NGINX use the forwarded chain)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def request_user_id(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_opt)]) -> Optional[uuid.UUID]:
    """Best-effort user id from an optional Bearer token — never raises.

    Returns None for guests so endpoints can apply their guest policy.
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return uuid.UUID(payload["sub"])
    except Exception:
        return None


def RateLimitDep(name: str, keyed_by_user: bool = False):
    """Build a dependency that enforces the named rate limit.

    keyed_by_user=False -> keyed by client IP (login, register, OTP mail).
    keyed_by_user=True  -> keyed by user id when authenticated, else IP.
    """

    async def _dep(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_opt)],
    ) -> None:
        if keyed_by_user and credentials is not None:
            uid = request_user_id(request, credentials)
            identity = f"user:{uid}" if uid is not None else f"ip:{client_ip(request)}"
        else:
            identity = f"ip:{client_ip(request)}"
        await check_rate_limit(name, identity)

    return Depends(_dep)


async def identity_for_request(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_opt)]) -> str:
    """Identity string for quota checks: 'user:<id>' or 'ip:<addr>'."""
    uid = request_user_id(request, credentials)
    return f"user:{uid}" if uid is not None else f"ip:{client_ip(request)}"
