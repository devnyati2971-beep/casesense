"""
Judgment read endpoints — Blueprint §11 (GET /judgments/{id}, /judgments/{id}/passages).
Judgments are shared library rows; any authenticated user may read them.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id, get_db
from app.core.exceptions import NotFoundException
from app.modules.judgements.models import Judgment, JudgmentPassage

router = APIRouter(prefix="/judgments", tags=["judgments"])


@router.get("/{judgment_id}")
async def get_judgment(
    judgment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    stmt = select(Judgment).where(Judgment.id == judgment_id)
    judgment = (await db.execute(stmt)).scalar_one_or_none()
    if not judgment:
        raise NotFoundException("Judgment not found.")
    return {
        "judgment": {
            "id": str(judgment.id),
            "case_name": judgment.title,
            "citation": judgment.citation,
            "court": judgment.court,
            "decided_on": judgment.decided_on.isoformat() if judgment.decided_on else None,
            "judges": judgment.judges,
            "source_url": judgment.source_url,
            "source": judgment.source,
        },
        "paragraphs": judgment.passages_metadata or [],
    }


@router.get("/{judgment_id}/passages")
async def get_judgment_passages(
    judgment_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    stmt = select(Judgment).where(Judgment.id == judgment_id)
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise NotFoundException("Judgment not found.")

    pstmt = (
        select(JudgmentPassage)
        .where(JudgmentPassage.judgment_id == judgment_id)
        .order_by(JudgmentPassage.created_at.asc())
        .limit(limit)
    )
    passages = list((await db.execute(pstmt)).scalars().all())
    return {
        "items": [
            {
                "id": str(p.id),
                "text": p.text,
                "location_label": f"Para {p.paragraph_number}" if p.paragraph_number else None,
            }
            for p in passages
        ],
        "next_cursor": None,
    }