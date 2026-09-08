import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_current_user_id, get_db
from app.modules.case_intelligence.schemas import (
    AnalyzeAcceptedResponse,
    CaseIntelligencePatchRequest,
    CaseIntelligenceResponse,
    LegalIssueResponse,
)
from app.modules.case_intelligence.service import CaseIntelligenceService

router = APIRouter(prefix="/matters/{matter_id}", tags=["case_intelligence"])


@router.post(
    "/analyze",
    response_model=AnalyzeAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AI case intelligence analysis",
)
async def analyze_matter(
    matter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = CaseIntelligenceService(db)
    latest, issues, job_id = await service.trigger_analysis(matter_id, user_id)
    
    # If no intelligence exists yet, return a skeleton response
    intel_data = latest.intelligence if latest else {}
    version = latest.version if latest else 0
    status_str = latest.status if latest else "DRAFT"

    return AnalyzeAcceptedResponse(
        intelligence=CaseIntelligenceResponse(
            version=version,
            status=status_str,
            intelligence=intel_data,
            legal_issues=[LegalIssueResponse.model_validate(i) for i in issues],
        ),
        job_id=job_id,
        status_url=f"/api/v1/matters/{matter_id}/intelligence",
    )


@router.get(
    "/intelligence",
    response_model=CaseIntelligenceResponse,
    summary="Get confirmed or draft case intelligence",
)
async def get_intelligence(
    matter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = CaseIntelligenceService(db)
    latest, issues = await service.get_intelligence(matter_id, user_id)
    return CaseIntelligenceResponse(
        version=latest.version,
        status=latest.status,
        intelligence=latest.intelligence,
        legal_issues=[LegalIssueResponse.model_validate(i) for i in issues],
    )


@router.patch(
    "/intelligence",
    response_model=CaseIntelligenceResponse,
    summary="Update case intelligence or toggle legal issues",
)
async def patch_intelligence(
    matter_id: uuid.UUID,
    body: CaseIntelligencePatchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = CaseIntelligenceService(db)
    saved_intel, issues = await service.patch_intelligence(
        matter_id=matter_id,
        user_id=user_id,
        intelligence_patch=body.intelligence,
        issue_updates=body.issue_updates,
    )
    return CaseIntelligenceResponse(
        version=saved_intel.version,
        status=saved_intel.status,
        intelligence=saved_intel.intelligence,
        legal_issues=[LegalIssueResponse.model_validate(i) for i in issues],
    )