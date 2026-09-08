import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_current_user_id, get_db
from app.modules.research.schemas import (
    CaseResearchRequest,
    ResearchAcceptedResponse,
    ResearchQueryRequest,
    ResearchSessionResponse,
    ResearchStatusResponse,
)
from app.modules.research.service import ResearchService

router = APIRouter(tags=["research"])


@router.post(
    "/research/query",
    response_model=ResearchAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="AI Citation Finder - Standalone Query Mode",
)
async def create_query_research(
    body: ResearchQueryRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = ResearchService(db)
    session_id, job_id = await service.initiate_query_research(
        user_id=user_id, query=body.query, matter_id=body.matter_id
    )
    return ResearchAcceptedResponse(
        session_id=session_id,
        status_url=f"/api/v1/research/{session_id}",
    )


@router.post(
    "/matters/{matter_id}/research",
    response_model=ResearchAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run targeted case research based on selected issues",
)
async def create_case_research(
    matter_id: uuid.UUID,
    body: CaseResearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = ResearchService(db)
    session_id, job_id = await service.initiate_case_research(
        user_id=user_id, matter_id=matter_id, issue_ids=body.issue_ids, extra_context=body.extra_context
    )
    return ResearchAcceptedResponse(
        session_id=session_id,
        status_url=f"/api/v1/research/{session_id}",
    )


@router.get(
    "/research/{session_id}",
    response_model=ResearchStatusResponse,
    summary="Poll research execution status and fetch results",
)
async def get_research_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = ResearchService(db)
    session = await service.get_session_status(session_id, user_id)
    
    # Return canonical status payload (§74.2)
    return ResearchStatusResponse(
        entity_id=session.id,
        status=session.status,
        stage=session.last_stage or session.status,
        results=session.error if session.status == "COMPLETED" else None # Hackathon UI data bridge
    )


@router.get(
    "/research",
    summary="List all research sessions for user",
)
async def list_research(
    limit: int = 50,
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = ResearchService(db)
    items, next_cursor = await service.list_sessions(user_id, limit, cursor)
    return {
        "items": [ResearchSessionResponse.model_validate(i) for i in items],
        "next_cursor": next_cursor,
    }