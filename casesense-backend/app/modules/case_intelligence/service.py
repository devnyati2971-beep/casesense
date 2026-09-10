import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.exceptions import NotFoundException
from app.modules.audit.service import AuditService
from app.modules.matters.models import Matter
from app.modules.case_intelligence.models import CaseIntelligence, LegalIssue
from app.modules.case_intelligence.repository import CaseIntelligenceRepository
from app.modules.case_intelligence.schemas import LegalIssueUpdate
from app.jobs.state import get_arq_redis


class CaseIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CaseIntelligenceRepository(db)

    async def verify_matter_access(self, matter_id: uuid.UUID, user_id: uuid.UUID) -> Matter:
        stmt = select(Matter).where(
            Matter.id == matter_id,
            Matter.owner_id == user_id,
            Matter.status != "DELETED",
        )
        result = await self.db.execute(stmt)
        matter = result.scalar_one_or_none()
        if not matter:
            raise NotFoundException(
                message="Matter not found", details={"matter_id": str(matter_id)}
            )
        return matter

    async def trigger_analysis(
        self, matter_id: uuid.UUID, user_id: uuid.UUID, force: bool = False
    ) -> Tuple[Optional[CaseIntelligence], List[LegalIssue], str]:
        await self.verify_matter_access(matter_id, user_id)
        latest = await self.repo.get_latest_intelligence(matter_id)
        issues = await self.repo.list_legal_issues(matter_id)

        job_id = f"intel_{matter_id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool is not None:
            await pool.enqueue_job("analyze_case", str(matter_id), _job_id=job_id)

        await AuditService.log(
            db=self.db,
            user_id=user_id,
            matter_id=matter_id,
            action="INTELLIGENCE_GENERATE",
            resource_type="CASE_INTELLIGENCE",
            resource_id=str(latest.id) if latest else "none",
            detail={"force": force},
        )
        return latest, issues, job_id

    async def get_intelligence(
        self, matter_id: uuid.UUID, user_id: uuid.UUID
    ) -> Tuple[CaseIntelligence, List[LegalIssue]]:
        await self.verify_matter_access(matter_id, user_id)
        latest = await self.repo.get_latest_intelligence(matter_id)
        if not latest:
            raise NotFoundException(
                message="Case intelligence has not been generated yet for this matter",
                details={"matter_id": str(matter_id)},
            )
        issues = await self.repo.list_legal_issues(matter_id)
        return latest, issues

    async def patch_intelligence(
        self,
        matter_id: uuid.UUID,
        user_id: uuid.UUID,
        intelligence_patch: Optional[dict],
        issue_updates: Optional[List[LegalIssueUpdate]],
    ) -> Tuple[CaseIntelligence, List[LegalIssue]]:
        await self.verify_matter_access(matter_id, user_id)
        latest = await self.repo.get_latest_intelligence(matter_id)
        if not latest:
            raise NotFoundException(
                message="Case intelligence not found", details={"matter_id": str(matter_id)}
            )

        # Apply lawyer corrections to JSON payload
        updated_intel_data = dict(latest.intelligence)
        if intelligence_patch:
            updated_intel_data.update(intelligence_patch)

        # Create new version per no-overwrite rule
        new_version = latest.version + 1
        new_record = CaseIntelligence(
            matter_id=matter_id,
            version=new_version,
            status="CONFIRMED",
            intelligence=updated_intel_data,
            ai_request_id=latest.ai_request_id,
        )
        saved_intel = await self.repo.create_intelligence(new_record)

        # Update legal issues if provided
        if issue_updates is not None:
            await self.db.execute(delete(LegalIssue).where(LegalIssue.matter_id == matter_id))
            new_issues = []
            for idx, upd in enumerate(issue_updates):
                new_issues.append(
                    LegalIssue(
                        matter_id=matter_id,
                        intelligence_id=saved_intel.id,
                        title=upd.title,
                        is_selected=upd.is_selected,
                        display_order=upd.display_order or idx,
                        origin="LAWYER_CONFIRMED",
                    )
                )
            await self.repo.save_legal_issues(new_issues)

        await self.db.commit()
        issues = await self.repo.list_legal_issues(matter_id)

        await AuditService.log(
            db=self.db,
            user_id=user_id,
            matter_id=matter_id,
            action="INTELLIGENCE_EDIT",
            resource_type="CASE_INTELLIGENCE",
            resource_id=str(saved_intel.id),
            detail={"version": new_version},
        )
        return saved_intel, issues