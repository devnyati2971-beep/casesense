import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.case_intelligence.models import CaseIntelligence, LegalIssue
from app.modules.documents.models import DocumentChunk


class CaseIntelligenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_intelligence(self, matter_id: uuid.UUID) -> Optional[CaseIntelligence]:
        stmt = (
            select(CaseIntelligence)
            .where(CaseIntelligence.matter_id == matter_id)
            .order_by(CaseIntelligence.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_intelligence(self, intel: CaseIntelligence) -> CaseIntelligence:
        self.db.add(intel)
        await self.db.flush()
        await self.db.refresh(intel)
        return intel

    async def list_legal_issues(self, matter_id: uuid.UUID) -> List[LegalIssue]:
        stmt = (
            select(LegalIssue)
            .where(LegalIssue.matter_id == matter_id)
            .order_by(LegalIssue.display_order.asc(), LegalIssue.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def save_legal_issues(self, issues: List[LegalIssue]) -> None:
        self.db.add_all(issues)
        await self.db.flush()

    async def get_matter_chunks(self, matter_id: uuid.UUID) -> List[DocumentChunk]:
        from app.modules.documents.models import Document
        stmt = (
            select(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.matter_id == matter_id, Document.status == "PROCESSED")
            .order_by(DocumentChunk.seq.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())