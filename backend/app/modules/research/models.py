"""
Research query and result models — blueprint §7, §22.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import ResearchStatus
from app.db.base import Base


class ResearchQuery(Base):
    __tablename__ = "research_queries"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiated_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("propositions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ResearchStatus.PENDING.value
    )
    job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    results: Mapped[list["ResearchResult"]] = relationship(
        "ResearchResult",
        back_populates="query",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class ResearchResult(Base):
    __tablename__ = "research_results"

    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_queries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    judgment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("judgments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relevance_score: Mapped[float | None] = mapped_column(nullable=True)
    relevance_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_by_lawyer: Mapped[bool] = mapped_column(nullable=False, default=False)

    query: Mapped["ResearchQuery"] = relationship(
        "ResearchQuery", back_populates="results", lazy="noload"
    )