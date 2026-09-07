"""
Citation model — blueprint §7, §26, §27.
Every citation traces to a specific passage in a real judgment.
RULE: No source = no citation.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import CitationStatus, CitationVerificationMethod
from app.db.base import Base


class Citation(Base):
    __tablename__ = "citations"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("propositions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    judgment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("judgments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("judgment_passages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # The exact quoted text from the source
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    paragraph_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=CitationStatus.UNVERIFIED.value
    )
    verification_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    similarity_score: Mapped[float | None] = mapped_column(nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Added by (AI or human)
    added_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_ai_suggested: Mapped[bool] = mapped_column(nullable=False, default=False)

    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)