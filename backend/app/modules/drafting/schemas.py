import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel

class CreateDraftRequest(BaseModel):
    document_type: str
    title: str

class DraftResponse(BaseModel):
    id: uuid.UUID
    matter_id: uuid.UUID
    document_type: str
    title: str
    status: str
    current_version: int

    model_config = {"from_attributes": True}

class QuestionnaireSubmitRequest(BaseModel):
    answers: Dict[str, str]

class QuestionnaireResponse(BaseModel):
    status: str
    questions: List[dict]

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