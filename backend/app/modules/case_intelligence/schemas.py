import uuid
from typing import List, Optional
from pydantic import BaseModel


class LegalIssueResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    confidence: Optional[str] = None
    origin: str
    is_selected: bool
    display_order: Optional[int] = 0

    model_config = {"from_attributes": True}


class CaseIntelligenceResponse(BaseModel):
    version: int
    status: str
    intelligence: dict
    legal_issues: List[LegalIssueResponse]

    model_config = {"from_attributes": True}


class AnalyzeAcceptedResponse(BaseModel):
    intelligence: CaseIntelligenceResponse
    job_id: str
    status_url: str


class LegalIssueUpdate(BaseModel):
    id: Optional[uuid.UUID] = None
    title: str
    is_selected: bool = True
    display_order: Optional[int] = 0


class CaseIntelligencePatchRequest(BaseModel):
    intelligence: Optional[dict] = None
    issue_updates: Optional[List[LegalIssueUpdate]] = None