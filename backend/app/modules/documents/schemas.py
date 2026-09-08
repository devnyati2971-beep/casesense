import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: uuid.UUID
    matter_id: uuid.UUID
    uploaded_by: uuid.UUID
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    status: str
    error_reason: Optional[str] = None
    page_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadAcceptedResponse(BaseModel):
    document: DocumentResponse
    job_id: str
    status_url: str


class DocumentStatusResponse(BaseModel):
    entity_id: uuid.UUID
    job_id: Optional[str] = None
    status: str
    stage: str
    progress: Optional[int] = None
    error_reason: Optional[str] = None
    page_count: Optional[int] = None


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    next_cursor: Optional[str] = None