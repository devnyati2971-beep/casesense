import uuid
from datetime import date, datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class CreateSavedCitationRequest(BaseModel):
    # Chain references (optional — verified when provided)
    authority_id: Optional[uuid.UUID] = None
    proposition_id: Optional[uuid.UUID] = None
    passage_id: Optional[uuid.UUID] = None
    judgment_id: Optional[uuid.UUID] = None

    # Inline citation data (used when chain rows are not yet persisted)
    case_name: str = Field(..., min_length=1, max_length=500)
    citation_text: Optional[str] = Field(None, max_length=200)
    court: Optional[str] = Field(None, max_length=200)
    decided_on: Optional[date] = None
    proposition_text: Optional[str] = None
    passage_text: Optional[str] = None
    location_label: Optional[str] = Field(None, max_length=120)
    support_state: Optional[str] = None

    # v2.2 UI fields
    citation_type: Optional[str] = Field(None, max_length=20)
    tags: Optional[List[str]] = None
    judges: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=200)
    related_provisions: Optional[List[str]] = None
    summary: Optional[str] = None

    note: Optional[str] = None
    label: Optional[str] = Field(None, max_length=100)


class UpdateSavedCitationRequest(BaseModel):
    note: Optional[str] = None
    label: Optional[str] = Field(None, max_length=100)


class SavedCitationResponse(BaseModel):
    id: uuid.UUID
    case_name: str
    citation_text: Optional[str] = None
    court: Optional[str] = None
    decided_on: Optional[date] = None
    proposition_text: Optional[str] = None
    passage_text: Optional[str] = None
    location_label: Optional[str] = None
    support_state: Optional[str] = None

    # v2.2 UI fields
    citation_type: Optional[str] = "judgment"
    tags: Optional[Union[list, None]] = None
    judges: Optional[Union[list, None]] = None
    category: Optional[str] = None
    related_provisions: Optional[Union[list, None]] = None
    summary: Optional[str] = None
    translated_passage: Optional[str] = None
    translated_at: Optional[datetime] = None

    note: Optional[str] = None
    label: Optional[str] = None
    authority_id: Optional[uuid.UUID] = None
    proposition_id: Optional[uuid.UUID] = None
    passage_id: Optional[uuid.UUID] = None
    judgment_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
