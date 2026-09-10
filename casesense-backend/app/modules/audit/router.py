"""
Audit endpoints — Blueprint §11 (GET /audit/matter/{id}).
Member-only; existence-hidden (404 for non-members).
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id, get_db
from app.core.exceptions import NotFoundException
from app.modules.audit.service import AuditService
from app.modules.matters.models import Matter

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/matter/{matter_id}")
async def list_matter_audit(
    matter_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    from sqlalchemy import select

    stmt = select(Matter).where(Matter.id == matter_id, Matter.owner_id == user_id)
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise NotFoundException("Matter not found.")

    items, next_cursor = await AuditService.list_matter_logs(
        db, matter_id, limit=limit, cursor=cursor
    )
    return {
        "items": [
            {
                "id": str(entry.id),
                "occurred_at": entry.created_at.isoformat() if entry.created_at else None,
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": str(entry.resource_id) if entry.resource_id else None,
                "user_id": str(entry.user_id) if entry.user_id else None,
                "detail": entry.extra_data,
            }
            for entry in items
        ],
        "next_cursor": next_cursor,
    }