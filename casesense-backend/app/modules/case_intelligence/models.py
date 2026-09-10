"""
Case Intelligence models — blueprint §7, §21.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CaseIntelligence(Base):
    __tablename__ = "case_intelligence"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    intelligence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ai_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    legal_issues: Mapped[list["LegalIssue"]] = relationship(
        "LegalIssue",
        back_populates="intelligence",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class LegalIssue(Base):
    __tablename__ = "legal_issues"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intelligence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("case_intelligence.id", ondelete="CASCADE"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    origin: Mapped[str] = mapped_column(String(30), nullable=False, default="AI_INFERENCE")
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    # ── Relationships ──────────────────────────────────────────────────────────
    intelligence: Mapped["CaseIntelligence"] = relationship(
        "CaseIntelligence", back_populates="legal_issues", lazy="noload"
    )