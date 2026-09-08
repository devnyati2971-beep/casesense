import uuid
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_current_user_id, get_db
from app.modules.drafting.schemas import (
    CreateDraftRequest,
    DraftResponse,
    DraftGenerateRequest,
    QuestionnaireSubmitRequest,
    QuestionnaireResponse,
    DraftExportRequest,
    DraftExportResponse
)
from app.modules.drafting.service import DraftingService
from app.modules.drafting.templates import DOCUMENT_TYPES
from app.modules.drafting.questionnaire import AutoFillEngine

router = APIRouter(tags=["drafting"])


@router.get("/document-types", summary="List available document types")
async def list_document_types():
    return [{"id": k, "display_name": v.display_name, "purpose": v.purpose} for k, v in DOCUMENT_TYPES.items()]


@router.post("/matters/{matter_id}/drafts", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    matter_id: uuid.UUID,
    body: CreateDraftRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    draft = await service.create_draft(matter_id, user_id, body.document_type, body.title)
    return DraftResponse.model_validate(draft)


@router.get("/drafts/{draft_id}/questionnaire", response_model=QuestionnaireResponse)
async def get_questionnaire(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    draft = await service.repo.get_draft_by_id(draft_id)
    quest = await service.repo.get_questionnaire(draft_id)
    q_data = AutoFillEngine.generate_questionnaire(draft.document_type, {})
    return QuestionnaireResponse(status=quest.status if quest else "SUBMITTED", questions=q_data["questions"])


@router.put("/drafts/{draft_id}/questionnaire")
async def submit_questionnaire(
    draft_id: uuid.UUID,
    body: QuestionnaireSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    await service.submit_questionnaire(draft_id, user_id, body.answers)
    return {"status": "BRIEF_READY"}


@router.post("/drafts/{draft_id}/brief", status_code=status.HTTP_201_CREATED)
async def generate_brief_snapshot(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    snapshot = await service.generate_brief_snapshot(draft_id, user_id)
    return {"brief_snapshot_id": snapshot.id, "brief": snapshot.brief}


@router.post("/drafts/{draft_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_draft(
    draft_id: uuid.UUID,
    body: DraftGenerateRequest = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    job_id = await service.trigger_generation(draft_id, user_id)
    return {"draft": {"status": "GENERATING"}, "job_id": job_id}


@router.post("/drafts/{draft_id}/finalize")
async def finalize_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    await service.finalize_draft(draft_id, user_id)
    return {"status": "FINALIZED"}


@router.post("/drafts/{draft_id}/exports", response_model=DraftExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_export(
    draft_id: uuid.UUID,
    body: DraftExportRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    export_id, q_status = await service.request_export(draft_id, user_id, body.format, body.version_id)
    return DraftExportResponse(export_id=export_id, format=body.format, status="PENDING")


@router.get("/drafts/{draft_id}/exports")
async def get_exports(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    service = DraftingService(db)
    items = await service.get_exports(draft_id, user_id)
    return {"items": items}