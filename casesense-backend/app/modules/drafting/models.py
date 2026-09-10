"""
Drafting models — blueprint §7 (drafts table) + §D28 (annex additions).
Draft is a first-class entity, not just an AI text response.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    DraftDocumentType,
    DraftExportFormat,
    DraftExportStatus,
    DraftSectionOrigin,
    DraftSectionStatus,
    DraftStatus,
)
from app.db.base import Base


class Draft(Base):
    """
    Main draft workspace entity.
    Blueprint §D1 — Draft as a first-class entity with lifecycle.
    """

    __tablename__ = "drafts"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # DraftDocumentType value
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DraftStatus.DRAFT.value
    )

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Finalization
    final_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # FK to draft_versions — set on finalize
    final_content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    finalized_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    matter: Mapped["Matter"] = relationship(  # type: ignore[name-defined]
        "Matter", back_populates="drafts", lazy="noload"
    )
    versions: Mapped[list["DraftVersion"]] = relationship(
        "DraftVersion",
        back_populates="draft",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    sections: Mapped[list["DraftSection"]] = relationship(
        "DraftSection",
        back_populates="draft",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    questionnaire: Mapped["DraftQuestionnaire | None"] = relationship(
        "DraftQuestionnaire",
        back_populates="draft",
        lazy="noload",
        uselist=False,
        cascade="all, delete-orphan",
    )
    brief_snapshots: Mapped[list["MatterBriefSnapshot"]] = relationship(
        "MatterBriefSnapshot",
        back_populates="draft",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    exports: Mapped[list["DraftExport"]] = relationship(
        "DraftExport",
        back_populates="draft",
        lazy="noload",
        cascade="all, delete-orphan",
    )


class DraftVersion(Base):
    """
    Immutable version snapshot — blueprint §D14.
    Version 1 is immutable once created.
    """

    __tablename__ = "draft_versions"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    draft: Mapped["Draft"] = relationship(
        "Draft", back_populates="versions", lazy="noload"
    )


class DraftSection(Base):
    """
    Individual editable section of a draft — blueprint §D11, §D12, §D28.
    Lawyer edits are tracked via origin field.
    """

    __tablename__ = "draft_sections"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Provenance
    origin: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DraftSectionOrigin.AI_GENERATED.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DraftSectionStatus.ACTIVE.value
    )

    # For section-level regeneration preview (§D15)
    pending_regeneration_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Citation lineage: list of citation IDs used in this section
    citation_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    draft: Mapped["Draft"] = relationship(
        "Draft", back_populates="sections", lazy="noload"
    )


class DraftQuestionnaire(Base):
    """
    Per-draft questionnaire with auto-fill — blueprint §D5, §D6, §D7.
    """

    __tablename__ = "draft_questionnaires"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Answers keyed by question_id, with provenance tags
    answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Schema definition for this document type's questions
    schema_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    draft: Mapped["Draft"] = relationship(
        "Draft", back_populates="questionnaire", lazy="noload"
    )


class MatterBriefSnapshot(Base):
    """
    Matter Brief — preparation layer before generation — blueprint §D8.
    NOT the generated document. The review gate before generation.
    """

    __tablename__ = "matter_brief_snapshots"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot of matter context at time of brief creation
    matter_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    propositions_snapshot: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    authorities_snapshot: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    citations_snapshot: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Stale detection
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    draft: Mapped["Draft"] = relationship(
        "Draft", back_populates="brief_snapshots", lazy="noload"
    )


class DraftExport(Base):
    """
    Export record — blueprint §D21.
    """

    __tablename__ = "draft_exports"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf / docx
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DraftExportStatus.PENDING.value
    )
    storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    draft: Mapped["Draft"] = relationship(
        "Draft", back_populates="exports", lazy="noload"
    )