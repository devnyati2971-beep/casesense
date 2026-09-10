import uuid
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_current_user_id, get_db
from app.modules.authorities.schemas import (
    AuthorityResponse,
    NoteRequest,
    NoteResponse,
    SelectAuthorityRequest,
)
from app.modules.authorities.service import AuthorityService

router = APIRouter(tags=["authorities"])


@router.post(
    "/research/{session_id}/authorities",
    response_model=AuthorityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Select a verified authority",
)
async def select_authority(
    session_id: uuid.UUID,
    body: SelectAuthorityRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = AuthorityService(db)
    auth = await service.select_authority(
        user_id=user_id, session_id=session_id, proposition_id=body.proposition_id, judgment_id=body.judgment_id
    )
    return AuthorityResponse.model_validate(auth)


@router.delete(
    "/authorities/{authority_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a selected authority",
)
async def remove_authority(
    authority_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = AuthorityService(db)
    await service.remove_authority(user_id=user_id, authority_id=authority_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/authorities/{authority_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a note to a selected authority",
)
async def add_authority_note(
    authority_id: uuid.UUID,
    body: NoteRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = AuthorityService(db)
    note = await service.add_note(user_id=user_id, authority_id=authority_id, body=body.body)
    return NoteResponse.model_validate(note)


@router.get(
    "/authorities/{authority_id}/notes",
    summary="List notes for an authority",
)
async def list_authority_notes(
    authority_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = AuthorityService(db)
    items = await service.list_notes(authority_id=authority_id)
    return {"items": [NoteResponse.model_validate(i) for i in items]}