import uuid
import os
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
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
from app.jobs.tasks.document import extract_text_by_pages
from app.ai.orchestrator import get_ai_orchestrator

router = APIRouter(tags=["research"])


@router.post(
    "/research/document",
    response_model=ResearchAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Find authorities from an uploaded document without creating a matter",
)
async def create_document_research(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Extract a one-off document locally, then search authorities from its issues.

    This deliberately does not persist the binary or create a Matter. Matters
    are for case-file management; Citation Finder is for ad-hoc research.
    """
    suffix = os.path.splitext(file.filename or "")[1].lower()
    allowed = {".pdf", ".docx", ".txt"}
    if suffix not in allowed:
        raise HTTPException(status_code=422, detail="Upload a PDF, DOCX, or TXT file.")
    content = await file.read()
    if not content or len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="Document must be between 1 byte and 25 MB.")
    mime_type = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }[suffix]
    pages = await extract_text_by_pages(content, mime_type)
    text = "\n".join(page["text"] for page in pages).strip()
    if len(text) < 80:
        raise HTTPException(status_code=422, detail="No usable text found. Use a text-based PDF, DOCX, or TXT file.")

    prompt = f"""Extract one precise Indian legal research query from this document.
Return JSON only: {{"query": "..."}}. Include the governing statute/section and disputed issue where present. Do not use generic terms such as 'landmark judgment'.

DOCUMENT:\n{text[:12000]}"""
    ai = get_ai_orchestrator()
    query = ""
    try:
        import json
        parsed = json.loads(await ai.generate_json(prompt, max_tokens=180) or "{}")
        query = str(parsed.get("query") or "").strip()
    except Exception:
        pass
    if len(query) < 10:
        # A safe fallback makes the route usable during transient AI quota
        # limits, while still grounding the search in the uploaded document.
        query = " ".join(text.split())[:500]

    await check_rate_limit("research_query_user", f"user:{user_id}")
    service = ResearchService(db)
    session_id, _ = await service.initiate_query_research(
        user_id=user_id, query=query, matter_id=None
    )
    return ResearchAcceptedResponse(
        session_id=session_id,
        status_url=f"/api/v1/research/{session_id}",
    )


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
