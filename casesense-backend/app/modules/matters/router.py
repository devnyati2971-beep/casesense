"""
Matter endpoints — /api/v1/matters/*
Blueprint §11.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query, status

from app.common.dependencies import CurrentUserId, DbSession, PaginationDep
from app.common.enums import MatterStatus
from app.common.schemas import PaginatedResponse, SuccessResponse, paginated
from app.modules.matters.schemas import (
    MatterCreateRequest,
    MatterResponse,
    MatterUpdateRequest,
)
from app.modules.matters.service import MatterService

router = APIRouter(prefix="/matters", tags=["matters"])


@router.post("", response_model=SuccessResponse[MatterResponse], status_code=status.HTTP_201_CREATED)
async def create_matter(
    body: MatterCreateRequest,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[MatterResponse]:
    svc = MatterService(db)
    matter = await svc.create(current_user_id, body)
    return SuccessResponse(data=MatterResponse.model_validate(matter), message="Matter created.")


@router.get("", response_model=PaginatedResponse[MatterResponse])
async def list_matters(
    current_user_id: CurrentUserId,
    db: DbSession,
    pagination: PaginationDep,
    status_filter: Optional[MatterStatus] = Query(None, alias="status"),
) -> PaginatedResponse[MatterResponse]:
    svc = MatterService(db)
    matters, total = await svc.list(
        current_user_id,
        status=status_filter,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        **paginated(
            [MatterResponse.model_validate(m) for m in matters],
            total,
            pagination.page,
            pagination.page_size,
        )
    )


@router.get("/{matter_id}", response_model=SuccessResponse[MatterResponse])
async def get_matter(
    matter_id: uuid.UUID,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[MatterResponse]:
    svc = MatterService(db)
    matter = await svc.get(matter_id, current_user_id)
    return SuccessResponse(data=MatterResponse.model_validate(matter))


@router.patch("/{matter_id}", response_model=SuccessResponse[MatterResponse])
async def update_matter(
    matter_id: uuid.UUID,
    body: MatterUpdateRequest,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> SuccessResponse[MatterResponse]:
    svc = MatterService(db)
    matter = await svc.update(matter_id, current_user_id, body)
    return SuccessResponse(data=MatterResponse.model_validate(matter), message="Matter updated.")


@router.post("/{matter_id}/archive", response_model=SuccessResponse[MatterResponse])
async def archive_matter(
    matter_id: uuid.UUID,
    current_user_id: CurrentUserId,
    db: DbSession,
    version: int = Query(..., description="Current version for optimistic locking"),
) -> SuccessResponse[MatterResponse]:
    svc = MatterService(db)
    matter = await svc.archive(matter_id, current_user_id, version)
    return SuccessResponse(data=MatterResponse.model_validate(matter), message="Matter archived.")


@router.post("/{matter_id}/restore", response_model=SuccessResponse[MatterResponse])
async def restore_matter(
    matter_id: uuid.UUID,
    current_user_id: CurrentUserId,
    db: DbSession,
    version: int = Query(..., description="Current version for optimistic locking"),
) -> SuccessResponse[MatterResponse]:
    svc = MatterService(db)
    matter = await svc.restore(matter_id, current_user_id, version)
    return SuccessResponse(data=MatterResponse.model_validate(matter), message="Matter restored.")


@router.post("/{matter_id}/delete", response_model=SuccessResponse[MatterResponse])
async def delete_matter(
    matter_id: uuid.UUID,
    current_user_id: CurrentUserId,
    db: DbSession,
    version: int = Query(..., description="Current version for optimistic locking"),
) -> SuccessResponse[MatterResponse]:
    svc = MatterService(db)
    matter = await svc.delete(matter_id, current_user_id, version)
    return SuccessResponse(data=MatterResponse.model_validate(matter), message="Matter deleted.")


@router.get("/{matter_id}/brief", summary="Matter Brief read-model (§1.4-C4)")
async def matter_brief(
    matter_id: uuid.UUID,
    current_user_id: CurrentUserId,
    db: DbSession,
) -> dict:
    svc = MatterService(db)
    return await svc.brief(matter_id, current_user_id)