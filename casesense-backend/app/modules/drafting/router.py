import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id, get_db
from app.core.exceptions import ValidationException
from app.modules.drafting.schemas import (
    CreateDraftRequest,
    DraftExportRequest,
    DraftExportResponse,
    DraftGenerateRequest,
    DraftPatchRequest,
    DraftResponse,
    QuestionnaireResponse,
    QuestionnaireSubmitRequest,
)
from app.modules.drafting.service import DraftingService
from app.modules.drafting.templates import DOCUMENT_TYPES

router = APIRouter(tags=["drafting"])


@router.get("/drafts", summary="List all drafts across matters (History/Drafting view)")
async def list_all_drafts(
    limit: int = 50,
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    items, next_cursor = await service.list_all_drafts(user_id, limit=limit, cursor=cursor)
    return {"items": items, "next_cursor": next_cursor}


@router.get("/document-types", summary="List available document types (§D22)")
async def list_document_types():
    return [
        {
            "id": config.id,
            "display_name": config.display_name,
            "purpose": config.purpose,
            "required_sections": config.required_sections,
            "questionnaire_summary": config.questionnaire_summary,
        }
        for config in DOCUMENT_TYPES.values()
    ]


@router.post(
    "/matters/{matter_id}/drafts",
    response_model=DraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft(
    matter_id: uuid.UUID,
    body: CreateDraftRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    draft = await service.create_draft(matter_id, user_id, body.document_type, body.title)
    return DraftResponse.model_validate(draft)


@router.get("/matters/{matter_id}/drafts", summary="List drafts for a matter")
async def list_drafts(
    matter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    drafts = await service.list_drafts(matter_id, user_id)
    return {"items": [DraftResponse.model_validate(d) for d in drafts]}


@router.get("/drafts/{draft_id}", response_model=dict, summary="Get draft with current version")
async def get_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    detail = await service.get_draft_detail(draft_id, user_id)
    return {
        "draft": DraftResponse.model_validate(detail["draft"]).model_dump(),
        "current_version": {
            "version": detail["current_version"]["version"],
            "sections": [
                {
                    "id": str(s.id),
                    "section_key": s.section_key,
                    "title": s.title,
                    "content": s.content,
                    "order_index": s.order_index,
                    "origin": s.origin,
                    "status": s.status,
                }
                for s in detail["current_version"]["sections"]
            ],
            "arguments": detail["current_version"]["arguments"],
            "citations": detail["current_version"]["citations"],
        },
    }


@router.patch("/drafts/{draft_id}", response_model=DraftResponse)
async def patch_draft(
    draft_id: uuid.UUID,
    body: DraftPatchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    draft = await service.patch_draft(
        draft_id,
        user_id,
        expected_version=body.expected_version,
        sections=body.sections,
        title=body.title,
    )
    return DraftResponse.model_validate(draft)


@router.get(
    "/drafts/{draft_id}/questionnaire",
    response_model=QuestionnaireResponse,
    summary="Get questionnaire with auto-filled values (§D6–D7)",
)
async def get_questionnaire(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    data = await service.get_questionnaire(draft_id, user_id)
    return QuestionnaireResponse(
        status=data["status"],
        questions=data["questions"],
        missing_required=data["missing_required"],
        progress=data["progress"],
    )


@router.put("/drafts/{draft_id}/questionnaire", summary="Submit questionnaire answers")
async def submit_questionnaire(
    draft_id: uuid.UUID,
    body: QuestionnaireSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    result = await service.submit_questionnaire(draft_id, user_id, body.answers)
    return {"status": result["status"], "remaining_required": result["remaining_required"]}


@router.post("/drafts/{draft_id}/brief", status_code=status.HTTP_201_CREATED)
async def generate_brief_snapshot(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    snapshot = await service.generate_brief_snapshot(draft_id, user_id)
    return {"brief_snapshot_id": str(snapshot.id)}


@router.get("/drafts/{draft_id}/brief", summary="Reviewable Matter Brief (§D8)")
async def get_brief(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    return await service.get_brief(draft_id, user_id)


@router.post("/drafts/{draft_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_draft(
    draft_id: uuid.UUID,
    body: Optional[DraftGenerateRequest] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    job_id = await service.trigger_generation(
        draft_id, user_id, argument_focus=body.argument_focus if body else None
    )
    return {
        "draft": {"status": "GENERATING"},
        "job_id": job_id,
        "status_url": f"/api/v1/drafts/{draft_id}",
    }


@router.post("/drafts/{draft_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_draft(
    draft_id: uuid.UUID,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    job_id = await service.regenerate_draft(
        draft_id, user_id, instructions=(body or {}).get("instructions")
    )
    return {
        "draft": {"status": "REGENERATING"},
        "job_id": job_id,
        "status_url": f"/api/v1/drafts/{draft_id}",
    }


@router.get("/drafts/{draft_id}/versions", summary="Version lineage (§D14)")
async def list_versions(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    versions = await service.list_versions(draft_id, user_id)
    return {"items": versions, "next_cursor": None}


@router.get("/drafts/{draft_id}/traceability", summary="Citation chain (§D33)")
async def traceability(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    return await service.traceability(draft_id, user_id)


@router.get("/drafts/{draft_id}/validation", summary="§D19 pre-finalization checklist")
async def get_validation(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    return await service.get_validation(draft_id, user_id)


@router.post("/drafts/{draft_id}/finalize", response_model=DraftResponse)
async def finalize_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    draft = await service.finalize_draft(draft_id, user_id)
    return DraftResponse.model_validate(draft)


@router.post(
    "/drafts/{draft_id}/exports",
    response_model=DraftExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_export(
    draft_id: uuid.UUID,
    body: DraftExportRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    if body.format not in ("pdf", "docx"):
        raise ValidationException("Unsupported export format — must be 'pdf' or 'docx'.")
    service = DraftingService(db)
    export_id, _ = await service.request_export(
        draft_id, user_id, body.format, body.version_id
    )
    return DraftExportResponse(
        export_id=export_id,
        format=body.format,
        status="PENDING",
        download_url=None,
    )


@router.get("/drafts/{draft_id}/exports")
async def get_exports(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DraftingService(db)
    items = await service.get_exports(draft_id, user_id)
    return {"items": items}