import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    query_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    concept_set_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CREATED"
    )
    last_stage: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    error: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("mode IN ('CASE', 'QUERY')", name="chk_research_mode"),
        CheckConstraint(
            "status IN ('CREATED', 'RETRIEVING', 'ANALYZING', 'VERIFYING', 'COMPLETED', 'FAILED')",
            name="chk_research_status",
        ),
        Index("ix_research_sessions_matter_created", "matter_id", "created_at"),
    )


class ResearchQuery(Base):
    __tablename__ = "research_queries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    concept: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    generated_by: Mapped[str] = mapped_column(String(20), default="AI", nullable=False)
    rank: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )