"""
Matter model — blueprint §7 matters table.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import MatterStatus, MatterType
from app.db.base import Base


class Matter(Base):
    __tablename__ = "matters"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    matter_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=MatterType.OTHER.value
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=MatterStatus.ACTIVE.value
    )
    court_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    opposite_party: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Relationships ──────────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="matters", lazy="noload"
    )
    documents: Mapped[list["Document"]] = relationship(  # type: ignore[name-defined]
        "Document", back_populates="matter", lazy="noload", cascade="all, delete-orphan"
    )
    drafts: Mapped[list["Draft"]] = relationship(  # type: ignore[name-defined]
        "Draft", back_populates="matter", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Matter {self.title[:40]}>"