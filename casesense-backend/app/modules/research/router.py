import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_current_user_id, get_db
from app.common.rate_limit import check_rate_limit, peek_guest_quota
from app.common.rate_limit_deps import RateLimitDep, client_ip, request_user_id
from app.modules.research.schemas import (
    CaseResearchRequest,
    ResearchAcceptedResponse,
    ResearchQueryRequest,
    ResearchSessionResponse,
    ResearchStatusResponse,
)
from app.modules.research.service import ResearchService

router = APIRouter(tags=["research"])


async def _quota_payload(identity: str) -> dict:
    """Remaining free guest searches, for the guest-limit dialog on the client."""
    remaining = await peek_guest_quota(identity)
    if remaining is None:
        return {"guest_searches_remaining": None}
    return {
        "guest_searches_remaining": remaining,
        "guest_search_limit": 2,
        "requires_registration": remaining <= 0,
    }


@router.post(
    "/research/query",
    response_model=ResearchAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="AI Citation Finder - Standalone Query Mode (guests allowed, 2 free searches / 24h)",
)
async def create_query_research(
    body: ResearchQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[uuid.UUID] = Depends(request_user_id),
):
    # v2.2 guest tier: anonymous callers may run up to 2 searches / 24h per IP.
    if user_id is None:
        await check_rate_limit("research_query_guest", f"ip:{client_ip(request)}")
        guest_key = client_ip(request)
        quota = await _quota_payload(f"ip:{guest_key}")
    else:
        await check_rate_limit("research_query_user", f"user:{user_id}")
        guest_key = None
        quota = {}

    service = ResearchService(db)
    session_id, job_id = await service.initiate_query_research(
        user_id=user_id, query=body.query, matter_id=body.matter_id, guest_key=guest_key
    )
    return ResearchAcceptedResponse(
        session_id=session_id,
        status_url=f"/api/v1/research/{session_id}",
        **quota,
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
    _rl: None = RateLimitDep("research_case", keyed_by_user=True),
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[uuid.UUID] = Depends(request_user_id),
):
    service = ResearchService(db)
    guest_key = client_ip(request) if user_id is None else None
    session = await service.get_session_status(session_id, user_id, guest_key=guest_key)

    # Canonical status payload (§30.3 / §74.2) — results surface when COMPLETED.
    return ResearchStatusResponse(
        entity_id=session.id,
        status=session.status,
        stage=session.last_stage or session.status,
        progress=None,
        results=session.results if session.status == "COMPLETED" else None,
        error=session.error if session.status == "FAILED" else None,
        created_by=session.created_by,
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
