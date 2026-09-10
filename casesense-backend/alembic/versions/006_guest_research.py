"""Guest research sessions — nullable created_by

Revision ID: 006_guest_research
Revises: 005_oauth_identities
Create Date: 2026-09-09

v2.2 guest tier: anonymous Citation Finder searches are allowed (2 / 24h per
IP, enforced by §75.1 rate limiting), so research_sessions.created_by becomes
nullable. NULL created_by marks a guest session.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_guest_research"
down_revision: Union[str, None] = "005_oauth_identities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "research_sessions",
        "created_by",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.add_column(
        "research_sessions",
        sa.Column("guest_key", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    # Re-attach orphaned guest sessions to the first user before re-tightening.
    op.execute(
        """
        UPDATE research_sessions rs
        SET created_by = u.id
        FROM (SELECT id FROM users ORDER BY created_at LIMIT 1) u
        WHERE rs.created_by IS NULL
        """
    )
    op.alter_column(
        "research_sessions",
        "created_by",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.drop_column("research_sessions", "guest_key")
