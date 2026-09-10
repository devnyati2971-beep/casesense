"""
Matter request/response schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import MatterStatus, MatterType


class MatterCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    matter_type: MatterType = MatterType.OTHER
    court_name: str | None = Field(None, max_length=500)
    case_number: str | None = Field(None, max_length=200)
    client_name: str | None = Field(None, max_length=500)
    opposite_party: str | None = Field(None, max_length=500)


class MatterUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    matter_type: MatterType | None = None
    status: MatterStatus | None = None
    court_name: str | None = Field(None, max_length=500)
    case_number: str | None = Field(None, max_length=200)
    client_name: str | None = Field(None, max_length=500)
    opposite_party: str | None = Field(None, max_length=500)
    version: int = Field(..., description="Current version for optimistic locking")


class MatterResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    matter_type: str
    status: str
    court_name: str | None
    case_number: str | None
    client_name: str | None
    opposite_party: str | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}