"""
Document and DocumentChunk models — blueprint §7.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.common.enums import DocumentStatus, DocumentType
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(200), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentType.OTHER.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=DocumentStatus.PENDING.value
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    matter: Mapped["Matter"] = relationship(  # type: ignore[name-defined]
        "Matter", back_populates="documents", lazy="noload"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document {self.original_filename}>"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # pgvector embedding — 1536 dims (OpenAI ada-002 / text-embedding-3-small)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    document: Mapped["Document"] = relationship(
        "Document", back_populates="chunks", lazy="noload"
    )