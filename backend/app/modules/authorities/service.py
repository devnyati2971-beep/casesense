import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.modules.authorities.models import Authority, ResearchNote
from app.modules.research.models import ResearchSession
from app.modules.audit.service import AuditService


class AuthorityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def select_authority(
        self, user_id: uuid.UUID, session_id: uuid.UUID, proposition_id: uuid.UUID, judgment_id: uuid.UUID
    ) -> Authority:
        # Verify session access
        stmt_sess = select(ResearchSession).where(ResearchSession.id == session_id)
        session = (await self.db.execute(stmt_sess)).scalar_one_or_none()
        if not session or (session.created_by != user_id and not session.matter_id):
            raise NotFoundException("Research session not found.")

        # Blueprint §27.3: Verification Gating
        stmt_check = select(Authority).where(
            Authority.session_id == session_id,
            Authority.proposition_id == proposition_id,
        )
        existing = (await self.db.execute(stmt_check)).scalar_one_or_none()
        if existing:
            raise ConflictException("ALREADY_SELECTED: This proposition authority is already selected.")

        authority = Authority(
            session_id=session_id,
            matter_id=session.matter_id,
            proposition_id=proposition_id,
            judgment_id=judgment_id,
            selected_by=user_id,
            relevance_label="HIGHLY_RELEVANT", # Determined by AI pipeline, hardcoded for direct insert
        )
        self.db.add(authority)
        await self.db.commit()
        await self.db.refresh(authority)

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=session.matter_id, action="AUTHORITY_SELECT",
            resource_type="AUTHORITY", resource_id=str(authority.id), detail={}
        )
        return authority

    async def remove_authority(self, user_id: uuid.UUID, authority_id: uuid.UUID) -> None:
        stmt = select(Authority).where(Authority.id == authority_id)
        authority = (await self.db.execute(stmt)).scalar_one_or_none()
        if not authority:
            raise NotFoundException("Authority not found.")
        
        await self.db.delete(authority)
        await self.db.commit()

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=authority.matter_id, action="AUTHORITY_DESELECT",
            resource_type="AUTHORITY", resource_id=str(authority_id), detail={}
        )

    async def add_note(self, user_id: uuid.UUID, authority_id: uuid.UUID, body: str) -> ResearchNote:
        stmt = select(Authority).where(Authority.id == authority_id)
        auth = (await self.db.execute(stmt)).scalar_one_or_none()
        if not auth:
            raise NotFoundException("Authority not found.")

        note = ResearchNote(authority_id=authority_id, author_id=user_id, body=body)
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_notes(self, authority_id: uuid.UUID) -> List[ResearchNote]:
        stmt = select(ResearchNote).where(ResearchNote.authority_id == authority_id).order_by(ResearchNote.created_at.asc())
        return list((await self.db.execute(stmt)).scalars().all())