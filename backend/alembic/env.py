"""
Alembic async migration environment.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base  # noqa: F401

# Import models for Alembic autogenerate
from app.modules.users.models import User  # noqa: E402, F401
from app.modules.matters.models import Matter  # noqa: E402, F401
from app.modules.documents.models import Document, DocumentChunk  # noqa: E402, F401
from app.modules.case_intelligence.models import CaseIntelligence, Proposition  # noqa: E402, F401
from app.modules.research.models import ResearchQuery, ResearchResult  # noqa: E402, F401
from app.modules.judgements.models import Judgment  # noqa: E402, F401
from app.modules.citations.models import Citation  # noqa: E402, F401
from app.modules.authorities.models import Authority  # noqa: E402, F401
from app.modules.drafting.models import (  # noqa: E402, F401
    Draft,
    DraftVersion,
    DraftSection,
    DraftQuestionnaire,
    MatterBriefSnapshot,
    DraftExport,
)
from app.modules.audit.models import AuditLog  # noqa: E402, F401
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()