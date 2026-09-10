import uuid
from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.documents.models import Document, DocumentChunk, DocumentPage


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, document: Document) -> Document:
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        stmt = select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_matter_and_hash(
        self, matter_id: uuid.UUID, sha256_hash: str
    ) -> Optional[Document]:
        stmt = select(Document).where(
            Document.matter_id == matter_id,
            Document.sha256 == sha256_hash,
            Document.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_matter(
        self, matter_id: uuid.UUID, limit: int = 50, cursor: Optional[str] = None
    ) -> List[Document]:
        stmt = (
            select(Document)
            .where(
                Document.matter_id == matter_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc(), Document.id.desc())
            .limit(limit + 1)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        error_reason: Optional[str] = None,
        page_count: Optional[int] = None,
    ) -> None:
        values = {"status": status, "updated_at": func.now()}
        if error_reason is not None:
            values["error_reason"] = error_reason
        if page_count is not None:
            values["page_count"] = page_count

        stmt = update(Document).where(Document.id == document_id).values(**values)
        await self.db.execute(stmt)
        await self.db.flush()

    async def save_pages(self, pages: List[DocumentPage]) -> None:
        self.db.add_all(pages)
        await self.db.flush()

    async def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        self.db.add_all(chunks)
        await self.db.flush()

    async def soft_delete(self, document_id: uuid.UUID) -> None:
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(deleted_at=func.now(), updated_at=func.now())
        )
        await self.db.execute(stmt)
        await self.db.flush()