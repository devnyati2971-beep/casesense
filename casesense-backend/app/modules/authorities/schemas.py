import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SelectAuthorityRequest(BaseModel):
    proposition_id: uuid.UUID
    judgment_id: uuid.UUID


class AuthorityResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    proposition_id: uuid.UUID
    judgment_id: uuid.UUID
    relevance_label: str
    note: Optional[str] = None
    selected_at: datetime

    model_config = {"from_attributes": True}


class NoteRequest(BaseModel):
    body: str = Field(..., max_length=5000)


class NoteResponse(BaseModel):
    id: uuid.UUID
    authority_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}