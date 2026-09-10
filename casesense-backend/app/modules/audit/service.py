"""
Audit service — write and read audit log entries (Blueprint §50).
Append-only; content bodies are never logged.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


class AuditService:
    """All audit writes flow through `AuditService.log(...)`.

    Call pattern (used across every module):
        await AuditService.log(
            db=session,
            user_id=...,
            matter_id=...,
            action="...",
            resource_type="...",
            resource_id=...,
            detail={...},   # metadata only — never content
        )
    """

    @classmethod
    async def log(
        cls,
        db: AsyncSession,
        action: str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | str | None = None,
        matter_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        extra_data: dict | None = None,
        detail: dict | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id if isinstance(resource_id, uuid.UUID) else (
                uuid.UUID(resource_id) if resource_id else None
            ),
            matter_id=matter_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data if extra_data is not None else detail,
            success=success,
            error_message=error_message,
        )
        db.add(entry)
        await db.flush()
        return entry

    @classmethod
    async def list_matter_logs(
        cls,
        db: AsyncSession,
        matter_id: uuid.UUID,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[AuditLog], str | None]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.matter_id == matter_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit + 1)
        )
        rows = list((await db.execute(stmt)).scalars().all())
        next_cursor = str(rows[-1].id) if len(rows) > limit else None
        return rows[:limit], next_cursor

    @classmethod
    async def count_for_matter(cls, db: AsyncSession, matter_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(AuditLog).where(AuditLog.matter_id == matter_id)
        return (await db.execute(stmt)).scalar_one()