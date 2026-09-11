"""
CaseSense FastAPI application entry point.
Blueprint §3, §4, §13 (error envelope), §53 (health checks).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import CaseSenseError
from app.core.logging import configure_logging, get_logger
from app.db.engine import engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger.info("CaseSense backend starting", env=settings.APP_ENV)
    yield
    logger.info("CaseSense backend shutting down")
    await engine.dispose()


def _error_envelope(exc: CaseSenseError, trace_id: str | None = None) -> dict:
    """Blueprint §13 error envelope — {success, error: {code, message, details}}."""
    return {
        "success": False,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details or None,
        },
        "trace_id": trace_id,
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="CaseSense API",
        description="Citation-grounded legal intelligence platform for Indian advocates.",
        version="2.2.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS (explicit allow-list — no wildcards, §16/§38.1) ───────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=r"^https?://localhost:\d+$" if settings.is_development else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────

    from fastapi.exceptions import RequestValidationError

    from fastapi.encoders import jsonable_encoder

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = request.headers.get("X-Request-ID")
        errors = exc.errors()
        message = "Validation Error"
        if errors:
            msg = errors[0].get("msg", "")
            loc = " -> ".join([str(x) for x in errors[0].get("loc", [])])
            message = f"{msg} ({loc})"

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_envelope(
                CaseSenseError(
                    message=message,
                    code="VALIDATION_ERROR",
                    details={"errors": jsonable_encoder(errors)},
                ),
                trace_id,
            ),
            headers={"X-Request-ID": trace_id} if trace_id else None,
        )

    @app.exception_handler(CaseSenseError)
    async def casesense_error_handler(request: Request, exc: CaseSenseError) -> JSONResponse:
        trace_id = request.headers.get("X-Request-ID")
        if exc.status_code >= 500:
            logger.error(
                "Application error",
                code=exc.code,
                message=exc.message,
                path=request.url.path,
            )
        response = JSONResponse(
            status_code=exc.status_code,
            content=_error_envelope(exc, trace_id),
            headers={"X-Request-ID": trace_id} if trace_id else None,
        )
        if getattr(exc, "background_tasks", None):
            response.background = exc.background_tasks
        return response

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc, path=request.url.path)
        trace_id = request.headers.get("X-Request-ID")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                CaseSenseError(
                    message="An unexpected error occurred.",
                    code="INTERNAL_ERROR",
                ),
                trace_id,
            ),
            headers={"X-Request-ID": trace_id} if trace_id else None,
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.modules.users.router import auth_router, oauth_router, users_router
    from app.modules.matters.router import router as matters_router
    from app.modules.documents.router import router as documents_router
    from app.modules.case_intelligence.router import router as case_intelligence_router
    from app.modules.research.router import router as research_router
    from app.modules.authorities.router import router as authorities_router
    from app.modules.drafting.router import router as drafting_router
    from app.modules.audit.router import router as audit_router
    from app.modules.saved_citations.router import router as saved_citations_router
    from app.modules.judgements.router import router as judgments_router
    from app.modules.ai_router import router as ai_router

    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(oauth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(matters_router, prefix=api_prefix)
    app.include_router(documents_router, prefix=api_prefix)
    app.include_router(case_intelligence_router, prefix=api_prefix)
    app.include_router(research_router, prefix=api_prefix)
    app.include_router(authorities_router, prefix=api_prefix)
    app.include_router(drafting_router, prefix=api_prefix)
    app.include_router(audit_router, prefix=api_prefix)
    app.include_router(saved_citations_router, prefix=api_prefix)
    app.include_router(judgments_router, prefix=api_prefix)
    app.include_router(ai_router, prefix=api_prefix)

    # ── Health (§53) ──────────────────────────────────────────────────────────

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {
            "status": "ok",
            "version": "2.2.0",
            "environment": settings.APP_ENV,
        }

    @app.get("/api/v1/health", tags=["health"])
    async def api_health() -> dict:
        return {
            "status": "ok",
            "version": "2.2.0",
            "environment": settings.APP_ENV,
        }

    @app.get("/ready", tags=["health"])
    async def readiness_check() -> JSONResponse:
        """DB + Redis dependency check — 503 with {db, redis} when unhealthy (§53)."""
        db_ok, redis_ok = await _check_dependencies()
        if db_ok and redis_ok:
            return JSONResponse(status_code=200, content={"status": "ready", "db": True, "redis": True})
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": db_ok, "redis": redis_ok},
        )

    @app.get("/live", tags=["health"])
    async def liveness_check() -> dict:
        return {"status": "alive"}

    return app


async def _check_dependencies() -> tuple[bool, bool]:
    db_ok = redis_ok = False
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        from app.jobs.state import get_arq_redis

        pool = await get_arq_redis()
        if pool is not None:
            await pool.ping()
            redis_ok = True
    except Exception:
        redis_ok = False
    return db_ok, redis_ok


app = create_app()
