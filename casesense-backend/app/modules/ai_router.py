"""
Standalone AI text utilities — v2.2 translate action.

POST /api/v1/translate {text, target_language} -> {translated_text}
Uses the AI orchestrator; deterministic dev fallback marks stub output.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id, get_db
from app.common.rate_limit_deps import RateLimitDep
from app.ai.orchestrator import get_ai_orchestrator

router = APIRouter(tags=["ai"])


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    target_language: str = Field("hi", max_length=10)


class TranslateResponse(BaseModel):
    translated_text: str
    target_language: str


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(
    body: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    user_id=Depends(get_current_user_id),
    _rl: None = RateLimitDep("ai_translate", keyed_by_user=True),
):
    """AI usage is rate limited per user (10/min) to protect the token budget (§75.1)."""
    orchestrator = get_ai_orchestrator()
    translated = await orchestrator.translate_to_hindi(body.text)
    return TranslateResponse(
        translated_text=translated or f"[HI] {body.text}",
        target_language=body.target_language,
    )
