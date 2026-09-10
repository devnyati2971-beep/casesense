import hashlib
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.logging import get_logger
from app.modules.matters.models import Matter
from app.modules.research.models import ResearchSession
from app.jobs.state import get_arq_redis
from app.modules.audit.service import AuditService

logger = get_logger(__name__)


class ResearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _verify_access(self, user_id: uuid.UUID, matter_id: Optional[uuid.UUID]) -> None:
        if matter_id:
            stmt = select(Matter).where(
                Matter.id == matter_id,
                Matter.owner_id == user_id,
                Matter.status != "DELETED",
            )
            matter = (await self.db.execute(stmt)).scalar_one_or_none()
            if not matter:
                raise NotFoundException("Matter not found or access denied.")

    async def initiate_query_research(
        self,
        user_id: Optional[uuid.UUID],
        query: str,
        matter_id: Optional[uuid.UUID],
        guest_key: Optional[str] = None,
    ) -> Tuple[uuid.UUID, str]:
        await self._verify_access(user_id, matter_id)

        session_id = uuid.uuid4()
        session = ResearchSession(
            id=session_id,
            matter_id=matter_id,
            created_by=user_id,
            mode="QUERY",
            query_text=query,
            status="CREATED",
            guest_key=guest_key,
        )
        self.db.add(session)
        await self.db.commit()

        # Enqueue job — enqueue failures degrade to a logged mock job id (§30),
        # the API response must never 500 because the queue is briefly down.
        job_id = f"res_{session_id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            try:
                await pool.enqueue_job("execute_research", str(session_id), _job_id=job_id)
            except Exception as exc:
                logger.warning("Failed to enqueue research job; degraded mode", error=str(exc))

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=matter_id, action="RESEARCH_START",
            resource_type="RESEARCH_SESSION", resource_id=str(session_id),
            detail={"mode": "QUERY", "guest_key": guest_key} if guest_key else {"mode": "QUERY"}
        )
        return session_id, job_id

    async def initiate_case_research(
        self, user_id: uuid.UUID, matter_id: uuid.UUID, issue_ids: Optional[List[uuid.UUID]], extra_context: Optional[str]
    ) -> Tuple[uuid.UUID, str]:
        await self._verify_access(user_id, matter_id)

        # Concept deduplication hash logic
        concept_raw = f"{matter_id}_{','.join(map(str, issue_ids or []))}_{extra_context or ''}"
        concept_hash = hashlib.sha256(concept_raw.encode("utf-8")).hexdigest()

        # Prevent concurrent identical research
        stmt = select(ResearchSession).where(
            ResearchSession.matter_id == matter_id,
            ResearchSession.concept_set_hash == concept_hash,
            ResearchSession.status.in_(["CREATED", "RETRIEVING", "ANALYZING", "VERIFYING"])
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ConflictException("RESEARCH_IN_PROGRESS: Identical research is currently running.")

        session_id = uuid.uuid4()
        session = ResearchSession(
            id=session_id,
            matter_id=matter_id,
            created_by=user_id,
            mode="CASE",
            concept_set_hash=concept_hash,
            status="CREATED",
        )
        self.db.add(session)
        await self.db.commit()

        job_id = f"res_{session_id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            try:
                await pool.enqueue_job("execute_research", str(session_id), _job_id=job_id)
            except Exception as exc:
                logger.warning("Failed to enqueue research job; degraded mode", error=str(exc))

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=matter_id, action="RESEARCH_START",
            resource_type="RESEARCH_SESSION", resource_id=str(session_id), detail={"mode": "CASE"}
        )
        return session_id, job_id

    async def get_session_status(
        self, session_id: uuid.UUID, user_id: Optional[uuid.UUID], guest_key: Optional[str] = None
    ) -> ResearchSession:
        stmt = select(ResearchSession).where(ResearchSession.id == session_id)
        session = (await self.db.execute(stmt)).scalar_one_or_none()
        if not session:
            raise NotFoundException("Research session not found.")

        # Guest sessions: readable only with the same guest key (IP) that created them.
        if session.created_by is None:
            if guest_key is None or session.guest_key != guest_key:
                raise NotFoundException("Research session not found.")
            return session

        # Enforce creator or matter member
        if session.created_by != user_id:
            if session.matter_id:
                await self._verify_access(user_id, session.matter_id)
            else:
                raise NotFoundException("Research session not found.")

        return session

    async def list_sessions(
        self, user_id: uuid.UUID, limit: int = 50, cursor: Optional[str] = None
    ) -> Tuple[List[ResearchSession], Optional[str]]:
        stmt = (
            select(ResearchSession)
            .where(
                ResearchSession.created_by == user_id,
                ResearchSession.created_by.is_not(None),
            )
            .order_by(ResearchSession.created_at.desc(), ResearchSession.id.desc())
            .limit(limit + 1)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        next_cursor = str(items[-1].id) if len(items) > limit else None
        return items[:limit], next_cursor