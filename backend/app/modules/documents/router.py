import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Header, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.common.dependencies import get_current_user_id, get_db
from app.modules.documents.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadAcceptedResponse,
)
from app.modules.documents.service import DocumentService

router = APIRouter(tags=["documents"])


@router.post(
    "/matters/{matter_id}/documents",
    response_model=DocumentUploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload document to matter",
)
async def upload_document(
    matter_id: uuid.UUID,
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DocumentService(db)
    doc, job_id = await service.upload_document(
        matter_id=matter_id, user_id=user_id, file=file
    )
    return DocumentUploadAcceptedResponse(
        document=DocumentResponse.model_validate(doc),
        job_id=job_id,
        status_url=f"/api/v1/documents/{doc.id}/status",
    )


@router.get(
    "/matters/{matter_id}/documents",
    response_model=DocumentListResponse,
    summary="List all documents for a matter",
)
async def list_documents(
    matter_id: uuid.UUID,
    limit: int = 50,
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DocumentService(db)
    items, next_cursor = await service.list_documents(
        matter_id=matter_id, user_id=user_id, limit=limit, cursor=cursor
    )
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in items],
        next_cursor=next_cursor,
    )


@router.get(
    "/documents/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Poll document processing status",
)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DocumentService(db)
    doc = await service.get_document_status(document_id, user_id)
    return DocumentStatusResponse(
        entity_id=doc.id,
        status=doc.status,
        stage=doc.status,
        error_reason=doc.error_reason,
        page_count=doc.page_count,
    )


@router.get(
    "/documents/{document_id}/download",
    summary="Generate pre-signed download redirect for document",
)
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DocumentService(db)
    url = await service.get_download_url(document_id, user_id)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DocumentService(db)
    await service.soft_delete(document_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documents/{document_id}/retry",
    response_model=DocumentUploadAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry processing for a failed document",
)
async def retry_document_processing(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    service = DocumentService(db)
    doc, job_id = await service.retry_processing(document_id, user_id)
    return DocumentUploadAcceptedResponse(
        document=DocumentResponse.model_validate(doc),
        job_id=job_id,
        status_url=f"/api/v1/documents/{doc.id}/status",
    )