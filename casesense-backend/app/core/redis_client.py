"""
Shared async Redis client (cache, rate limits, OAuth state).

Separate from the Arq job-transport pool (app/jobs/state.py) — this is the
plain redis.asyncio client used by app infrastructure.
"""

from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Optional[Redis] = None


async def get_redis() -> Optional[Redis]:
    """Return a shared Redis client, or None when Redis is unreachable."""
    global _redis
    if _redis is not None:
        try:
            await _redis.ping()
            return _redis
        except Exception:
            try:
                await _redis.aclose()
            except Exception:
                pass
            _redis = None
    try:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception as exc:
        logger.warning("Redis unavailable", error=str(exc))
        _redis = None
        return None


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except Exception:
            pass
        _redis = None
