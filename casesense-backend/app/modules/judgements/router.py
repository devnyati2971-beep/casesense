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
from app.modules.saved_citations.models import SavedCitation
from app.services.kanoon import KanoonService

router = APIRouter(prefix="/judgments", tags=["judgments"])


@router.get("/{judgment_id}/full-text")
async def get_full_judgment_text(
    judgment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    judgment = await db.get(Judgment, judgment_id)
    if not judgment:
        raise NotFoundException("Judgment not found.")
    return {"full_text": judgment.full_text or ""}


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
    graph = (judgment.extra_metadata or {}).get("citation_graph") or {}
    # Judgments saved before citation-graph support are refreshed lazily on
    # first read. This repairs existing History entries without a migration.
    if judgment.source == "indiankanoon" and judgment.external_id and not (
        graph.get("cited_authorities") or graph.get("cited_by")
    ):
        source_doc = await KanoonService().get_judgment(judgment.external_id)
        if source_doc:
            graph = {
                "cited_authorities": source_doc.get("cited_authorities", []),
                "cited_by": source_doc.get("cited_by", []),
            }
            judgment.extra_metadata = {**(judgment.extra_metadata or {}), "citation_graph": graph}
            await db.commit()
    citations = list(
        (
            await db.execute(
                select(SavedCitation)
                .where(
                    SavedCitation.judgment_id == judgment_id,
                    SavedCitation.user_id == user_id,
                )
                .order_by(SavedCitation.created_at.desc())
            )
        ).scalars()
    )
    research_passages = list(
        (
            await db.execute(
                select(JudgmentPassage)
                .where(JudgmentPassage.judgment_id == judgment_id)
                .order_by(JudgmentPassage.created_at.asc())
            )
        ).scalars()
    )
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
            "overview": (judgment.extra_metadata or {}).get("overview", {}),
        },
        "paragraphs": judgment.passages_metadata or [],
        "referencing_citations": [
            {
                "id": str(citation.id),
                "passage_text": citation.passage_text,
                "note": citation.note,
                "location_label": citation.location_label,
            }
            for citation in citations
        ],
        "cited_authorities": graph.get("cited_authorities", []),
        "cited_by": graph.get("cited_by", []),
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
