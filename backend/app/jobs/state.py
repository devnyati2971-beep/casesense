import uuid
from typing import Any, Optional
from redis.asyncio import Redis
from arq.connections import ArqRedis, create_pool, RedisSettings
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_arq_pool: Optional[ArqRedis] = None


async def get_arq_redis() -> Optional[ArqRedis]:
    """Retrieve or create an Arq connection pool."""
    global _arq_pool
    if _arq_pool is None:
        try:
            redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
            _arq_pool = await create_pool(redis_settings)
        except Exception as exc:
            logger.warning("Arq Redis connection failed; operating in degraded mode", error=str(exc))
            return None
    return _arq_pool


class JobQueueService:
    """Client helper to enqueue background tasks to Redis via Arq."""

    @staticmethod
    async def enqueue_document_processing(document_id: uuid.UUID) -> str:
        job_id = f"doc_{document_id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool is not None:
            try:
                await pool.enqueue_job(
                    "process_document",
                    str(document_id),
                    _job_id=job_id,
                    _queue_name="docs",
                )
                logger.info("Enqueued document processing job", job_id=job_id, document_id=str(document_id))
            except Exception as exc:
                logger.error("Failed to enqueue document to Arq", error=str(exc))
        else:
            logger.info("Redis not connected; mock job ID generated", job_id=job_id)
        return job_id