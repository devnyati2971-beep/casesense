import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id, get_db
from app.common.rate_limit_deps import RateLimitDep
from app.modules.saved_citations.schemas import (
    CreateSavedCitationRequest,
    SavedCitationResponse,
    UpdateSavedCitationRequest,
)
from app.modules.saved_citations.service import SavedCitationService

router = APIRouter(prefix="/saved-citations", tags=["saved-citations"])


@router.post("", response_model=SavedCitationResponse, status_code=status.HTTP_201_CREATED)
async def create_saved_citation(
    body: CreateSavedCitationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = SavedCitationService(db)
    saved = await service.create(user_id, body)
    return SavedCitationResponse.model_validate(saved)


@router.get("")
async def list_saved_citations(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = None,
    citation_type: Optional[str] = Query(None, description="judgment|act|article|other"),
    q: Optional[str] = Query(None, description="Case name search"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = SavedCitationService(db)
    items, next_cursor = await service.list_for_user(
        user_id, limit=limit, cursor=cursor, citation_type=citation_type, q=q
    )
    return {
        "items": [SavedCitationResponse.model_validate(i).model_dump() for i in items],
        "next_cursor": next_cursor,
    }


@router.get("/counts")
async def get_saved_citation_counts(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """v2.2 — per-type counts for the filter chips (All (12) Judgments (8) ...)."""
    service = SavedCitationService(db)
    return await service.counts(user_id)


@router.get("/{citation_id}", response_model=SavedCitationResponse)
async def get_saved_citation(
    citation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = SavedCitationService(db)
    saved = await service.get(user_id, citation_id)
    return SavedCitationResponse.model_validate(saved)


@router.patch("/{citation_id}", response_model=SavedCitationResponse)
async def update_saved_citation(
    citation_id: uuid.UUID,
    body: UpdateSavedCitationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = SavedCitationService(db)
    saved = await service.update(user_id, citation_id, body.note, body.label)
    return SavedCitationResponse.model_validate(saved)


@router.post("/{citation_id}/translate", response_model=SavedCitationResponse)
async def translate_saved_citation(
    citation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
    _rl: None = RateLimitDep("ai_saved_translate", keyed_by_user=True),
):
    """v2.2 — Translate to Hindi action (AI usage rate limited per user)."""
    service = SavedCitationService(db)
    saved = await service.translate(user_id, citation_id)
    return SavedCitationResponse.model_validate(saved)


@router.delete("/{citation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_citation(
    citation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = SavedCitationService(db)
    await service.delete(user_id, citation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
