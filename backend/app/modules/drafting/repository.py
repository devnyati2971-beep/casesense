import uuid
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.drafting.models import (
    Draft, 
    DraftQuestionnaire, 
    MatterBriefSnapshot, 
    DraftExport,
    DraftSection,
    DraftVersion
)

class DraftingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_draft(self, draft: Draft) -> Draft:
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def get_draft_by_id(self, draft_id: uuid.UUID) -> Optional[Draft]:
        stmt = select(Draft).where(Draft.id == draft_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_questionnaire(self, draft_id: uuid.UUID) -> Optional[DraftQuestionnaire]:
        stmt = select(DraftQuestionnaire).where(DraftQuestionnaire.draft_id == draft_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_draft_status(self, draft_id: uuid.UUID, status: str) -> None:
        stmt = update(Draft).where(Draft.id == draft_id).values(status=status)
        await self.db.execute(stmt)
        await self.db.flush()

    async def create_brief_snapshot(self, snapshot: MatterBriefSnapshot) -> MatterBriefSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)
        return snapshot

    # --- Export Methods ---

    async def create_export(self, export: DraftExport) -> DraftExport:
        self.db.add(export)
        await self.db.flush()
        await self.db.refresh(export)
        return export

    async def get_export_by_id(self, export_id: uuid.UUID) -> Optional[DraftExport]:
        stmt = select(DraftExport).where(DraftExport.id == export_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_exports(self, draft_id: uuid.UUID) -> List[DraftExport]:
        stmt = select(DraftExport).where(DraftExport.draft_id == draft_id).order_by(DraftExport.created_at.desc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def update_export_status(self, export_id: uuid.UUID, status: str, object_key: str = None) -> None:
        values = {"status": status}
        if object_key:
            values["object_key"] = object_key
        stmt = update(DraftExport).where(DraftExport.id == export_id).values(**values)
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_version_sections(self, version_id: uuid.UUID) -> List[DraftSection]:
        stmt = select(DraftSection).where(
            DraftSection.version_id == version_id,
            DraftSection.status == "ACTIVE"
        ).order_by(DraftSection.seq.asc())
        return list((await self.db.execute(stmt)).scalars().all())