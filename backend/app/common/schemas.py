"""
Standard API response envelopes and pagination schemas.
Blueprint §13.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope."""

    success: bool = True
    data: T
    message: str | None = None


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    error: str
    details: list[ErrorDetail] | None = None
    request_id: str | None = None


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list envelope."""

    success: bool = True
    data: list[T]
    meta: PaginationMeta


def paginated(
    items: list[Any],
    total: int,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Helper to build paginated response dict."""
    import math
    return {
        "success": True,
        "data": items,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if page_size else 1,
        },
    }


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str = "2.0.0"
    environment: str