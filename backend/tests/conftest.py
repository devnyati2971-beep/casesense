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
from app.db.engine import get_db
from app.main import app

# Use a separate test database URL
TEST_DB_URL = f"{settings.DATABASE_URL}_test"


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