"""
Judgment model — blueprint §7, §25.
Judgments are the authoritative legal source documents.
RULE: No source = no citation. Nothing is fabricated here.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
# pyrefly: ignore [missing-import]
from pgvector.sqlalchemy import Vector

from app.common.enums import CourtLevel, JudgmentSource
from app.db.base import Base


class Judgment(Base):
    __tablename__ = "judgments"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_judgments_source_external_id"),
    )

    # ── Source identity ────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default=JudgmentSource.INDIANKANOON.value
    )
    external_id: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ── Legal metadata ────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    citation: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    court: Mapped[str | None] = mapped_column(String(500), nullable=True)
    court_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decided_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    judges: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    subject_matter: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Content ───────────────────────────────────────────────────────────────
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_fetched: Mapped[bool] = mapped_column(nullable=False, default=False)
    # Document-level embedding for fast similarity
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # ── Passages (paragraphs) stored inline as JSONB list ─────────────────────
    # Each entry: {paragraph_number, text, embedding_stored_separately}
    passages_metadata: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    passages: Mapped[list["JudgmentPassage"]] = relationship(
        "JudgmentPassage",
        back_populates="judgment",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class JudgmentPassage(Base):
    """
    A single paragraph/passage from a judgment.
    Blueprint §26 — paragraph-level traceability.
    """

    __tablename__ = "judgment_passages"

    judgment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("judgments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paragraph_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    passage_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    judgment: Mapped["Judgment"] = relationship(
        "Judgment", back_populates="passages", lazy="noload"
    )