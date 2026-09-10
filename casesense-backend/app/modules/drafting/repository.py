import uuid
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.drafting.models import (
    Draft,
    DraftExport,
    DraftQuestionnaire,
    DraftSection,
    DraftVersion,
    MatterBriefSnapshot,
)


class DraftingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Drafts ─────────────────────────────────────────────────────────────────

    async def create_draft(self, draft: Draft) -> Draft:
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def get_draft_by_id(self, draft_id: uuid.UUID) -> Optional[Draft]:
        stmt = select(Draft).where(Draft.id == draft_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_matter(self, matter_id: uuid.UUID, limit: int = 50) -> List[Draft]:
        stmt = (
            select(Draft)
            .where(Draft.matter_id == matter_id)
            .order_by(Draft.created_at.desc(), Draft.id.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def update_draft_status(self, draft_id: uuid.UUID, status: str) -> None:
        await self.db.execute(
            update(Draft).where(Draft.id == draft_id).values(status=status)
        )
        await self.db.flush()

    async def update_draft(
        self, draft_id: uuid.UUID, expected_version: int, **fields
    ) -> Optional[Draft]:
        """Optimistic-locked update — 0 rows means version mismatch (§10, §D29)."""
        result = await self.db.execute(
            update(Draft)
            .where(Draft.id == draft_id, Draft.version == expected_version)
            .values(version=expected_version + 1, **fields)
            .returning(Draft)
        )
        return result.scalar_one_or_none()

    # ── Questionnaire ──────────────────────────────────────────────────────────

    async def get_questionnaire(self, draft_id: uuid.UUID) -> Optional[DraftQuestionnaire]:
        stmt = select(DraftQuestionnaire).where(DraftQuestionnaire.draft_id == draft_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def save_questionnaire_answers(
        self, draft_id: uuid.UUID, answers: dict, complete: bool
    ) -> None:
        await self.db.execute(
            update(DraftQuestionnaire)
            .where(DraftQuestionnaire.draft_id == draft_id)
            .values(answers=answers, is_complete=complete)
        )
        await self.db.flush()

    # ── Brief snapshots ────────────────────────────────────────────────────────

    async def create_brief_snapshot(self, snapshot: MatterBriefSnapshot) -> MatterBriefSnapshot:
        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_latest_brief(self, draft_id: uuid.UUID) -> Optional[MatterBriefSnapshot]:
        stmt = (
            select(MatterBriefSnapshot)
            .where(MatterBriefSnapshot.draft_id == draft_id)
            .order_by(MatterBriefSnapshot.created_at.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    # ── Versions & sections ────────────────────────────────────────────────────

    async def create_version(self, version: DraftVersion) -> DraftVersion:
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def get_latest_version(self, draft_id: uuid.UUID) -> Optional[DraftVersion]:
        stmt = (
            select(DraftVersion)
            .where(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_number.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_versions(self, draft_id: uuid.UUID) -> List[DraftVersion]:
        stmt = (
            select(DraftVersion)
            .where(DraftVersion.draft_id == draft_id)
            .order_by(DraftVersion.version_number.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def clear_current_flags(self, draft_id: uuid.UUID) -> None:
        await self.db.execute(
            update(DraftVersion)
            .where(DraftVersion.draft_id == draft_id)
            .values(is_current=False)
        )
        await self.db.flush()

    async def get_sections_for_version(self, version_id: uuid.UUID) -> List[DraftSection]:
        stmt = (
            select(DraftSection)
            .where(
                DraftSection.draft_version_id == version_id,
                DraftSection.status == "ACTIVE",
            )
            .order_by(DraftSection.order_index.asc(), DraftSection.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def save_sections(self, sections: List[DraftSection]) -> None:
        self.db.add_all(sections)
        await self.db.flush()

    async def update_section_content(
        self, section_id: uuid.UUID, content: str, title: str | None = None
    ) -> None:
        values: dict = {"content": content, "origin": "LAWYER_EDITED"}
        if title is not None:
            values["title"] = title
        await self.db.execute(
            update(DraftSection).where(DraftSection.id == section_id).values(**values)
        )
        await self.db.flush()

    # ── Exports ────────────────────────────────────────────────────────────────

    async def create_export(self, export: DraftExport) -> DraftExport:
        self.db.add(export)
        await self.db.flush()
        await self.db.refresh(export)
        return export

    async def get_export_by_id(self, export_id: uuid.UUID) -> Optional[DraftExport]:
        stmt = select(DraftExport).where(DraftExport.id == export_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_exports(self, draft_id: uuid.UUID) -> List[DraftExport]:
        stmt = (
            select(DraftExport)
            .where(DraftExport.draft_id == draft_id)
            .order_by(DraftExport.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def update_export_status(
        self,
        export_id: uuid.UUID,
        status: str,
        storage_key: str | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if storage_key is not None:
            values["storage_key"] = storage_key
        if error_message is not None:
            values["error_message"] = error_message
        await self.db.execute(
            update(DraftExport).where(DraftExport.id == export_id).values(**values)
        )
        await self.db.flush()