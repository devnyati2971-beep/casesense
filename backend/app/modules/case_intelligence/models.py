"""
CaseIntelligence and Proposition models — blueprint §7, §21.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import IntelligenceStatus, PropositionStatus
from app.db.base import Base


class CaseIntelligence(Base):
    __tablename__ = "case_intelligence"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One intelligence record per matter
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=IntelligenceStatus.PENDING.value
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_facts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    legal_issues: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    suggested_arguments: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Proposition(Base):
    """
    AI-extracted propositions from matter documents.
    Blueprint §26 — Passage + Proposition + Authority Model.
    """

    __tablename__ = "propositions"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_intelligence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=PropositionStatus.PENDING.value
    )
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)