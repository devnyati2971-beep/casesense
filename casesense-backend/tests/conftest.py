"""
Pytest fixtures for the CaseSense backend test suite.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

# pyrefly: ignore [missing-import]
import pytest_asyncio
# pyrefly: ignore [missing-import]
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.engine import get_db, job_session_factory
from app.main import app

# Use a separate test database URL
TEST_DB_URL = f"{settings.DATABASE_URL}_test"

# §75.1 rate limiting is environment-gated; tests exercise business logic, not
# quotas, and parallel test runs share a client IP. Disable for the suite.
settings.RATE_LIMITING_ENABLED = False


@pytest_asyncio.fixture(scope="session", autouse=True)
async def use_stub_ai_provider():
    """Keep tests deterministic even when a developer configured live AI."""
    import app.ai.orchestrator as orchestrator_module

    previous_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "stub"
    orchestrator_module._orchestrator = None
    yield
    settings.AI_PROVIDER = previous_provider
    orchestrator_module._orchestrator = None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create all tables once per test session."""
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    yield

    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def patch_job_session_factory():
    """Point background job tasks at the test database."""
    import importlib

    engine_module = importlib.import_module("app.db.engine")

    test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    test_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    engine_module.job_session_factory = test_factory
    yield
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client whose requests use the test database.

    Instead of sharing a pre-created session (which causes event-loop
    mismatch errors with asyncpg), we override get_db so that each
    ASGI request creates *its own* session from the test engine — exactly
    like production, but pointed at the test DB.
    """
    test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    test_session_factory = async_sessionmaker(
        bind=test_engine, expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
    await test_engine.dispose()
