"""v2.2 UI fields for saved citations

Revision ID: 004_saved_citation_ui_fields
Revises: 003_v22_lifecycle
Create Date: 2026-09-09

Adds the columns backing the Saved Citations detail panel and translate action:
citation_type, tags, judges, category, related_provisions, summary,
translated_passage, translated_at.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_saved_citation_ui_fields"
down_revision: Union[str, None] = "003_v22_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "saved_citations",
        sa.Column("citation_type", sa.String(20), nullable=True, server_default="judgment"),
    )
    op.create_index("ix_saved_citations_citation_type", "saved_citations", ["citation_type"])
    op.add_column("saved_citations", sa.Column("tags", postgresql.JSONB, nullable=True))
    op.add_column("saved_citations", sa.Column("judges", postgresql.JSONB, nullable=True))
    op.add_column("saved_citations", sa.Column("category", sa.String(200), nullable=True))
    op.create_index("ix_saved_citations_category", "saved_citations", ["category"])
    op.add_column("saved_citations", sa.Column("related_provisions", postgresql.JSONB, nullable=True))
    op.add_column("saved_citations", sa.Column("summary", sa.Text, nullable=True))
    op.add_column("saved_citations", sa.Column("translated_passage", sa.Text, nullable=True))
    op.add_column("saved_citations", sa.Column("translated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("saved_citations", "translated_at")
    op.drop_column("saved_citations", "translated_passage")
    op.drop_column("saved_citations", "summary")
    op.drop_column("saved_citations", "related_provisions")
    op.drop_index("ix_saved_citations_category", table_name="saved_citations")
    op.drop_column("saved_citations", "category")
    op.drop_column("saved_citations", "judges")
    op.drop_column("saved_citations", "tags")
    op.drop_index("ix_saved_citations_citation_type", table_name="saved_citations")
    op.drop_column("saved_citations", "citation_type")
