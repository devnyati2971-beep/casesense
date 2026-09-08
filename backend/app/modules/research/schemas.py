import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ResearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=10, max_length=500)
    matter_id: Optional[uuid.UUID] = None


class CaseResearchRequest(BaseModel):
    issue_ids: Optional[List[uuid.UUID]] = None
    extra_context: Optional[str] = None


class ResearchSessionResponse(BaseModel):
    id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    mode: str
    status: str
    last_stage: Optional[str] = None
    query_text: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchAcceptedResponse(BaseModel):
    session_id: uuid.UUID
    status_url: str


class ResearchStatusResponse(BaseModel):
    entity_id: uuid.UUID
    status: str
    stage: str
    progress: Optional[int] = None
    results: Optional[dict] = None