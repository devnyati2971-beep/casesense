import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CreateDraftRequest(BaseModel):
    document_type: str
    title: str = Field(..., min_length=1, max_length=500)


class DraftResponse(BaseModel):
    id: uuid.UUID
    matter_id: uuid.UUID
    document_type: str
    title: str
    status: str
    version: int
    created_at: object | None = None

    model_config = {"from_attributes": True}


class SectionPatchItem(BaseModel):
    id: uuid.UUID
    content: str = ""
    title: Optional[str] = None


class DraftPatchRequest(BaseModel):
    expected_version: int = Field(..., description="Optimistic-lock token (§D29)")
    sections: Optional[List[SectionPatchItem]] = None
    title: Optional[str] = None


class QuestionnaireSubmitRequest(BaseModel):
    answers: Dict[str, str]


class QuestionnaireResponse(BaseModel):
    status: str
    questions: List[dict]
    missing_required: List[str] = []
    progress: int = 0


class DraftGenerateRequest(BaseModel):
    argument_focus: Optional[str] = None
    section_hint: Optional[str] = None


class ValidationChecklistResponse(BaseModel):
    ready: bool
    blocking: List[dict]
    warnings: List[dict]


class DraftExportRequest(BaseModel):
    format: str = "pdf"
    version_id: Optional[uuid.UUID] = None


class DraftExportResponse(BaseModel):
    export_id: uuid.UUID
    format: str
    status: str
    download_url: Optional[str] = None