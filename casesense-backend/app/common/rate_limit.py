"""
Centralized rate limiting — Blueprint §75.1.

Sliding-window counters in Redis (INCR + EXPIRE — atomic, cheap). Every limit
is (max_requests, window_seconds) and keyed by a client identity:
authenticated user id when available, else client IP.

Endpoints currently enforced (§75.1 + v2.2 guest flow):
  - POST /auth/register                -> 50 / hour   per IP
  - POST /auth/login                   -> 10 / 5min  per IP
  - POST /auth/resend-verification     -> 1 / minute per IP+email  (OTP/email exhaustion guard)
  - POST /auth/forgot-password         -> 1 / minute per IP+email  (OTP/email exhaustion guard)
  - POST /auth/oauth/callback          -> 10 / 5min  per IP
  - POST /translate                    -> 10 / minute per user     (AI token guard)
  - POST /saved-citations/{id}/translate -> 10 / minute per user  (AI token guard)
  - POST /research/query               -> guests: 2 / 24h per IP; users: 20 / hour
  - POST /matters/{id}/research        -> 20 / hour per user
  - POST /matters/{id}/intelligence/regenerate (AI) -> 10 / hour per user

Fail-open philosophy: if Redis is unreachable the limiter degrades to an
in-process window so dev/demo never hard-fails; production sets REDIS_URL.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Limits registry (name -> (max requests, window seconds)) ──────────────────

RATE_LIMITS: dict[str, tuple[int, int]] = {
    "auth_register": (5, 3600),          # 5 registrations / hour / IP
    "auth_login": (10, 300),             # 10 login attempts / 5 min / IP
    "auth_resend_verification": (1, 60),  # 1 OTP mail / minute (email exhaustion guard)
    "auth_verify_email": (10, 600),       # 10 OTP attempts / 10 min per account
    "auth_forgot_password": (1, 60),      # 1 reset mail / minute (email exhaustion guard)
    "auth_oauth_callback": (10, 300),
    "ai_translate": (10, 60),            # 10 AI calls / minute / user (token guard)
    "ai_saved_translate": (10, 60),
    "research_query_guest": (2, 86400),  # 2 free searches / 24h / IP (v2.2 guest tier)
    "research_query_user": (20, 3600),   # 20 searches / hour / user
    "research_case": (20, 3600),
}

# ── In-memory fallback (used only when Redis is unreachable) ──────────────────

_local_buckets: dict[str, list[float]] = {}


def _memory_hit(key: str, limit: int, window: int) -> bool:
    """True when allowed. Sliding window over timestamps kept per key."""
    now = time.monotonic()
    bucket = [t for t in _local_buckets.get(key, []) if now - t < window]
    if len(bucket) >= limit:
        _local_buckets[key] = bucket
        return False
    bucket.append(now)
    _local_buckets[key] = bucket
    return True


async def check_rate_limit(name: str, identity: str) -> None:
    """Raise RateLimitError (429) when the caller exceeded the named limit."""
    from app.core.config import settings

    if not settings.RATE_LIMITING_ENABLED:
        return
    if name not in RATE_LIMITS:
        return
    limit, window = RATE_LIMITS[name]
    key = f"rl:{name}:{identity}"

    redis = None
    try:
        from app.core.redis_client import get_redis

        redis = await get_redis()
    except Exception:
        redis = None

    if redis is not None:
        try:
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            count, ttl = await pipe.execute()
            if int(count) == 1:
                await redis.expire(key, window)
                retry_after = window
            else:
                retry_after = int(ttl) if ttl and ttl > 0 else window
            if int(count) > limit:
                raise RateLimitError(
                    message="Rate limit exceeded. Please try again later.",
                    details={"retry_after_seconds": retry_after, "limit": limit, "window_seconds": window},
                )
            return
        except RateLimitError:
            raise
        except Exception as exc:  # Redis hiccup -> fall through to memory limiter
            logger.warning("Rate limiter Redis error; using in-memory fallback", error=str(exc))

    if not _memory_hit(key, limit, window):
        raise RateLimitError(
            message="Rate limit exceeded. Please try again later.",
            details={"limit": limit, "window_seconds": window},
        )


async def check_rate_limit_or_count(name: str, identity: str) -> Optional[int]:
    """Non-raising variant used for quota display (returns remaining or None)."""
    if name not in RATE_LIMITS:
        return None
    limit, window = RATE_LIMITS[name]
    key = f"rl:{name}:{identity}"
    redis = None
    try:
        from app.core.redis_client import get_redis

        redis = await get_redis()
    except Exception:
        redis = None
    if redis is not None:
        try:
            count = await redis.get(key)
            if count is None:
                return limit
            return max(0, limit - int(count))
        except Exception:
            pass
    now = time.monotonic()
    used = len([t for t in _local_buckets.get(key, []) if now - t < window])
    return max(0, limit - used)


async def peek_guest_quota(identity: str) -> Optional[int]:
    """Remaining free guest searches for the identity (None = unknown)."""
    return await check_rate_limit_or_count("research_query_guest", identity)
