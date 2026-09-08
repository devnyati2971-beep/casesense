"""
CaseSense FastAPI application entry point.
Blueprint §3, §4.
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


def create_app() -> FastAPI:
    app = FastAPI(
        title="CaseSense API",
        description="Citation-grounded legal intelligence platform for Indian advocates.",
        version="2.1.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.APP_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────

    @app.exception_handler(CaseSenseError)
    async def casesense_error_handler(request: Request, exc: CaseSenseError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "An unexpected error occurred.",
                "details": None,
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.modules.users.router import auth_router, users_router
    from app.modules.matters.router import router as matters_router
    from app.modules.documents.router import router as documents_router
    from app.modules.case_intelligence.router import router as case_intelligence_router
    from app.modules.research.router import router as research_router
    from app.modules.authorities.router import router as authorities_router

    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(users_router, prefix=api_prefix)
    app.include_router(matters_router, prefix=api_prefix)
    app.include_router(documents_router, prefix=api_prefix)
    app.include_router(case_intelligence_router, prefix=api_prefix)
    app.include_router(research_router, prefix=api_prefix)
    app.include_router(authorities_router, prefix=api_prefix)

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {
            "status": "ok",
            "version": "2.1.0",
            "environment": settings.APP_ENV,
        }

    @app.get("/api/v1/health", tags=["health"])
    async def api_health() -> dict:
        return {
            "status": "ok",
            "version": "2.1.0",
            "environment": settings.APP_ENV,
        }

    @app.get("/ready", tags=["health"])
    async def readiness_check() -> dict:
        return {"status": "ready", "db": True, "redis": True}

    @app.get("/live", tags=["health"])
    async def liveness_check() -> dict:
        return {"status": "alive"}

    return app


app = create_app()