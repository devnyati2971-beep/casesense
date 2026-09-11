"""
Matter service.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import MatterStatus
from app.core.exceptions import MatterAccessDeniedError, NotFoundError
from app.modules.matters.models import Matter
from app.modules.matters.repository import MatterRepository
from app.modules.matters.schemas import (
    MatterCreateRequest,
    MatterResponse,
    MatterUpdateRequest,
)


class MatterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MatterRepository(session)

    async def create(self, owner_id: uuid.UUID, data: MatterCreateRequest) -> Matter:
        return await self.repo.create(
            owner_id=owner_id,
            title=data.title,
            description=data.description,
            matter_type=data.matter_type.value,
            court_name=data.court_name,
            case_number=data.case_number,
            client_name=data.client_name,
            opposite_party=data.opposite_party,
        )

    async def get(self, matter_id: uuid.UUID, owner_id: uuid.UUID) -> Matter:
        matter = await self.repo.get_by_id_and_owner(matter_id, owner_id)
        if matter is None:
            # Don't reveal existence to unauthorized user
            raise MatterAccessDeniedError()
        return matter

    async def list(
        self,
        owner_id: uuid.UUID,
        status: MatterStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Matter], int]:
        return await self.repo.list_by_owner(owner_id, status, offset, limit)

    async def update(
        self, matter_id: uuid.UUID, owner_id: uuid.UUID, data: MatterUpdateRequest
    ) -> Matter:
        fields = {}
        if data.title is not None:
            fields["title"] = data.title
        if data.description is not None:
            fields["description"] = data.description
        if data.matter_type is not None:
            fields["matter_type"] = data.matter_type.value
        if data.status is not None:
            fields["status"] = data.status.value
        if data.court_name is not None:
            fields["court_name"] = data.court_name
        if data.case_number is not None:
            fields["case_number"] = data.case_number
        if data.client_name is not None:
            fields["client_name"] = data.client_name
        if data.opposite_party is not None:
            fields["opposite_party"] = data.opposite_party

        matter = await self.repo.update(matter_id, owner_id, data.version, **fields)
        if matter is None:
            raise MatterAccessDeniedError()
        return matter

    async def archive(
        self, matter_id: uuid.UUID, owner_id: uuid.UUID, version: int
    ) -> Matter:
        matter = await self.repo.archive(matter_id, owner_id, version)
        if matter is None:
            raise MatterAccessDeniedError()
        return matter

    async def restore(
        self, matter_id: uuid.UUID, owner_id: uuid.UUID, version: int
    ) -> Matter:
        matter = await self.repo.restore(matter_id, owner_id, version)
        if matter is None:
            raise MatterAccessDeniedError()
        return matter

    async def delete(
        self, matter_id: uuid.UUID, owner_id: uuid.UUID, version: int
    ) -> Matter:
        # Deleting a matter must also release every document object it owns.
        # Matter deletion remains soft in the database for audit purposes, but
        # the source files are no longer retained in object storage.
        from sqlalchemy import select

        from app.modules.documents.models import Document
        from app.modules.documents.service import DocumentService

        matter = await self.get(matter_id, owner_id)
        if matter.version != version:
            from app.core.exceptions import OptimisticLockError

            raise OptimisticLockError()

        documents = list(
            (
                await self.session.execute(
                    select(Document).where(
                        Document.matter_id == matter_id,
                        Document.deleted_at.is_(None),
                    )
                )
            ).scalars().all()
        )
        document_service = DocumentService(self.session)
        for document in documents:
            await document_service.soft_delete(document.id, owner_id)

        matter = await self.repo.soft_delete(matter_id, owner_id, version)
        if matter is None:
            raise MatterAccessDeniedError()
        return matter

    async def brief(self, matter_id: uuid.UUID, owner_id: uuid.UUID) -> dict:
        """Compiled Matter Brief — confirmed intelligence + selected authorities."""
        from sqlalchemy import select

        from app.modules.authorities.models import Authority
        from app.modules.case_intelligence.models import CaseIntelligence
        from app.modules.judgements.models import Judgment

        matter = await self.get(matter_id, owner_id)

        intel_stmt = (
            select(CaseIntelligence)
            .where(CaseIntelligence.matter_id == matter_id)
            .order_by(CaseIntelligence.version.desc())
            .limit(1)
        )
        intel = (await self.session.execute(intel_stmt)).scalar_one_or_none()

        auth_stmt = (
            select(Authority)
            .where(Authority.matter_id == matter_id)
            .order_by(Authority.selected_at.desc())
        )
        authorities = list((await self.session.execute(auth_stmt)).scalars().all())
        selected = []
        for authority in authorities:
            judgment = None
            if authority.judgment_id:
                jstmt = select(Judgment).where(Judgment.id == authority.judgment_id)
                judgment = (await self.session.execute(jstmt)).scalar_one_or_none()
            selected.append({
                "authority_id": str(authority.id),
                "case_name": judgment.title if judgment else None,
                "citation": judgment.citation if judgment else None,
                "court": judgment.court if judgment else None,
                "relevance_label": authority.relevance_label,
            })

        intelligence = intel.intelligence if intel else {}
        return {
            "matter": MatterResponse.model_validate(matter).model_dump(),
            "confirmed_intelligence": intelligence,
            "selected_authorities": selected,
            "timeline": intelligence.get("timeline", []),
        }
