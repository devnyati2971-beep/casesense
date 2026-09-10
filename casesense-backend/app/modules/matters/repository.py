"""
Matter repository.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import MatterStatus
from app.core.exceptions import OptimisticLockError
from app.modules.matters.models import Matter


class MatterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        owner_id: uuid.UUID,
        title: str,
        description: str | None,
        matter_type: str,
        court_name: str | None = None,
        case_number: str | None = None,
        client_name: str | None = None,
        opposite_party: str | None = None,
    ) -> Matter:
        matter = Matter(
            owner_id=owner_id,
            title=title,
            description=description,
            matter_type=matter_type,
            court_name=court_name,
            case_number=case_number,
            client_name=client_name,
            opposite_party=opposite_party,
        )
        self.session.add(matter)
        await self.session.flush()
        return matter

    async def get_by_id(self, matter_id: uuid.UUID) -> Matter | None:
        result = await self.session.execute(
            select(Matter).where(Matter.id == matter_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_owner(
        self, matter_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Matter | None:
        result = await self.session.execute(
            select(Matter).where(
                Matter.id == matter_id,
                Matter.owner_id == owner_id,
                Matter.status != "DELETED",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: uuid.UUID,
        status: MatterStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Matter], int]:
        query = select(Matter).where(
            Matter.owner_id == owner_id, Matter.status != "DELETED"
        )
        count_query = select(func.count()).select_from(Matter).where(
            Matter.owner_id == owner_id, Matter.status != "DELETED"
        )
        if status:
            query = query.where(Matter.status == status.value)
            count_query = count_query.where(Matter.status == status.value)

        query = query.order_by(Matter.updated_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        matters = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        return matters, total

    async def update(
        self,
        matter_id: uuid.UUID,
        owner_id: uuid.UUID,
        current_version: int,
        **fields,
    ) -> Matter | None:
        # Optimistic lock: only update if version matches
        result = await self.session.execute(
            update(Matter)
            .where(
                Matter.id == matter_id,
                Matter.owner_id == owner_id,
                Matter.version == current_version,
            )
            .values(version=current_version + 1, **fields)
            .returning(Matter)
        )
        updated = result.scalar_one_or_none()
        if updated is None:
            # Check if matter exists at all
            existing = await self.get_by_id_and_owner(matter_id, owner_id)
            if existing is None:
                return None
            raise OptimisticLockError()
        return updated

    async def archive(self, matter_id: uuid.UUID, owner_id: uuid.UUID, version: int) -> Matter | None:
        return await self.update(
            matter_id, owner_id, version, status=MatterStatus.ARCHIVED.value
        )

    async def restore(self, matter_id: uuid.UUID, owner_id: uuid.UUID, version: int) -> Matter | None:
        return await self.update(
            matter_id, owner_id, version, status=MatterStatus.ACTIVE.value
        )

    async def soft_delete(self, matter_id: uuid.UUID, owner_id: uuid.UUID, version: int) -> Matter | None:
        from datetime import datetime, timezone

        return await self.update(
            matter_id,
            owner_id,
            version,
            status="DELETED",
            extra_metadata=None,
        )