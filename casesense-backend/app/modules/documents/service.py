import hashlib
import uuid
from typing import List, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.modules.audit.service import AuditService
from app.modules.matters.models import Matter
from app.modules.documents.models import Document
from app.modules.documents.repository import DocumentRepository
from app.storage import get_storage_adapter
from app.jobs.state import JobQueueService

ALLOWED_MIME_TYPES = {
    "application/pdf": [b"%PDF"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK\x03\x04"],
    "text/plain": [],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)
        self.storage = get_storage_adapter()

    async def verify_matter_access(self, matter_id: uuid.UUID, user_id: uuid.UUID) -> Matter:
        from sqlalchemy import select
        stmt = select(Matter).where(
            Matter.id == matter_id,
            Matter.owner_id == user_id,
            Matter.status != "DELETED",
        )
        result = await self.db.execute(stmt)
        matter = result.scalar_one_or_none()
        if not matter:
            # Per Blueprint §15: Hide existence of foreign matters
            raise NotFoundException(
                message="Matter not found", details={"matter_id": str(matter_id)}
            )
        return matter

    async def upload_document(
        self, matter_id: uuid.UUID, user_id: uuid.UUID, file: UploadFile
    ) -> Tuple[Document, str]:
        await self.verify_matter_access(matter_id, user_id)

        # Read file contents and validate file size
        content = await file.read()
        size_bytes = len(content)
        if size_bytes > MAX_UPLOAD_SIZE:
            raise ValidationException(
                message="File size exceeds maximum permitted 25MB",
                details={"size_bytes": size_bytes, "max_allowed": MAX_UPLOAD_SIZE},
            )

        # MIME & magic byte check
        content_type = file.content_type or "application/octet-stream"
        if content_type not in ALLOWED_MIME_TYPES:
            raise ValidationException(
                message=f"Unsupported file MIME type: {content_type}",
                details={"allowed": list(ALLOWED_MIME_TYPES.keys())},
            )

        magic_signatures = ALLOWED_MIME_TYPES[content_type]
        if magic_signatures:
            matched = any(content.startswith(sig) for sig in magic_signatures)
            if not matched:
                raise ValidationException(
                    message="File magic bytes do not match declared MIME type",
                    details={"content_type": content_type},
                )

        # Calculate stream SHA256
        sha256_hash = hashlib.sha256(content).hexdigest()

        # Deduplication check: duplicate active document in matter
        existing = await self.repo.get_by_matter_and_hash(matter_id, sha256_hash)
        if existing:
            raise ConflictException(
                message="Duplicate document: an identical file is already active in this matter",
                details={"existing_document_id": str(existing.id), "sha256": sha256_hash},
            )

        # Generate unique storage key
        doc_id = uuid.uuid4()
        extension = file.filename.split(".")[-1] if "." in (file.filename or "") else "bin"
        object_key = f"matters/{matter_id}/documents/{doc_id}.{extension}"

        # Write to Object Storage
        await self.storage.put_object(
            key=object_key,
            data=content,
            content_type=content_type,
        )

        # Create database record
        doc = Document(
            id=doc_id,
            matter_id=matter_id,
            uploaded_by=user_id,
            file_name=file.filename or "unknown_file",
            mime_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            object_key=object_key,
            status="UPLOADED",
        )
        saved_doc = await self.repo.create(doc)

        # Audit log
        await AuditService.log(
            db=self.db,
            user_id=user_id,
            matter_id=matter_id,
            action="DOCUMENT_UPLOAD",
            resource_type="DOCUMENT",
            resource_id=str(doc.id),
            detail={
                "file_name": saved_doc.file_name,
                "size_bytes": size_bytes,
                "mime_type": content_type,
                "sha256": sha256_hash,
            },
        )

        # Enqueue background processing job
        job_id = await JobQueueService.enqueue_document_processing(doc_id)
        return saved_doc, job_id

    async def list_documents(
        self, matter_id: uuid.UUID, user_id: uuid.UUID, limit: int = 50, cursor: Optional[str] = None
    ) -> Tuple[List[Document], Optional[str]]:
        await self.verify_matter_access(matter_id, user_id)
        items = await self.repo.list_by_matter(matter_id, limit=limit, cursor=cursor)
        next_cursor = None
        if len(items) > limit:
            next_cursor = str(items[-1].id)
            items = items[:limit]
        return items, next_cursor

    async def get_document_status(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Document:
        doc = await self.repo.get_by_id(document_id)
        if not doc:
            raise NotFoundException(
                message="Document not found", details={"document_id": str(document_id)}
            )
        await self.verify_matter_access(doc.matter_id, user_id)
        return doc

    async def get_download_url(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> str:
        doc = await self.get_document_status(document_id, user_id)
        return await self.storage.generate_presigned_url(doc.object_key, expires_in=900)

    async def soft_delete(self, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
        doc = await self.get_document_status(document_id, user_id)
        await self.repo.soft_delete(doc.id)
        # A library delete is intended to release the user's storage quota, not
        # merely hide the row from the UI. The DB row remains soft-deleted for
        # auditability, while the binary object is removed from object storage.
        await self.storage.delete_object(doc.object_key)
        await AuditService.log(
            db=self.db,
            user_id=user_id,
            matter_id=doc.matter_id,
            action="DOCUMENT_DELETE",
            resource_type="DOCUMENT",
            resource_id=str(doc.id),
            detail={"file_name": doc.file_name, "sha256": doc.sha256},
        )

    async def retry_processing(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Tuple[Document, str]:
        doc = await self.get_document_status(document_id, user_id)
        if doc.status not in ("FAILED", "NEEDS_REVIEW"):
            raise ConflictException(
                message="Only FAILED or NEEDS_REVIEW documents can be retried",
                details={"current_status": doc.status},
            )

        await self.repo.update_status(document_id=doc.id, status="PROCESSING", error_reason=None)
        job_id = await JobQueueService.enqueue_document_processing(doc.id)
        return doc, job_id
