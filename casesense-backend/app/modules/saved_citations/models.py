"""
SavedCitation model — v2.2 (blueprint §7 addition).

The user's persistent personal citation collection, distinct from matter-level
authority selection. Deleting a saved citation never deletes the underlying
authority/proposition/passage (provenance survives).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SavedCitation(Base):
    __tablename__ = "saved_citations"
    __table_args__ = (
        UniqueConstraint("user_id", "judgment_id", "passage_id", name="uq_saved_citations_user_judgment_passage"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Chain references — SET NULL so saving/removing one never destroys provenance.
    authority_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True
    )
    proposition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("propositions.id", ondelete="SET NULL"), nullable=True
    )
    judgment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("judgments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("judgment_passages.id", ondelete="SET NULL"), nullable=True
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Denormalized display snapshot (works even when chain rows are absent in dev).
    case_name: Mapped[str] = mapped_column(String(500), nullable=False)
    citation_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    court: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decided_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    proposition_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    support_state: Mapped[str | None] = mapped_column(String(25), nullable=True)

    # ── v2.2 UI fields (mockup: Saved Citations detail panel) ──────────────────
    # citation_type: judgment | act | article | other (drives the filter chips)
    citation_type: Mapped[str | None] = mapped_column(String(20), nullable=True, default="judgment", index=True)
    # Display tags e.g. ["Constitutional Law", "Basic Structure"]
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Bench judges e.g. ["S.M. Sikri, J.", "A.N. Grover, J."]
    judges: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Category e.g. "Constitutional Law"
    category: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    # Related provisions e.g. ["Article 14", "Article 19", "Article 21"]
    related_provisions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Full judgment summary shown in the detail panel
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hindi translation (v2.2 translate action)
    translated_passage: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    judgment: Mapped["Judgment"] = relationship("Judgment", lazy="noload")  # type: ignore[name-defined]