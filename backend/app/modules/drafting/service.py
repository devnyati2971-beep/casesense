import hashlib
import json
import uuid
from typing import Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.exceptions import NotFoundException, ValidationException, ConflictException
from app.modules.matters.models import Matter
from app.modules.case_intelligence.models import CaseIntelligence
from app.modules.drafting.models import Draft, DraftQuestionnaire, MatterBriefSnapshot, DraftExport, DraftVersion
from app.modules.drafting.repository import DraftingRepository
from app.modules.drafting.questionnaire import AutoFillEngine
from app.modules.drafting.templates import DOCUMENT_TYPES
from app.storage import get_storage_adapter
from app.jobs.state import get_arq_redis


class DraftingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DraftingRepository(db)
        self.storage = get_storage_adapter()

    async def _verify_access(self, user_id: uuid.UUID, matter_id: uuid.UUID) -> None:
        stmt = select(Matter).where(Matter.id == matter_id, Matter.owner_id == user_id, Matter.status != "DELETED")
        if not (await self.db.execute(stmt)).scalar_one_or_none():
            raise NotFoundException("Matter not found or access denied.")

    async def create_draft(self, matter_id: uuid.UUID, user_id: uuid.UUID, doc_type: str, title: str) -> Draft:
        await self._verify_access(user_id, matter_id)
        if doc_type not in DOCUMENT_TYPES:
            raise ValidationException("Invalid document_type")

        draft = await self.repo.create_draft(Draft(
            matter_id=matter_id, created_by=user_id, document_type=doc_type, title=title, status="DRAFT_CREATED"
        ))
        
        stmt = select(CaseIntelligence).where(CaseIntelligence.matter_id == matter_id).order_by(CaseIntelligence.version.desc()).limit(1)
        intel = (await self.db.execute(stmt)).scalar_one_or_none()
        intel_data = intel.intelligence if intel else {}

        q_data = AutoFillEngine.generate_questionnaire(doc_type, intel_data)
        quest = DraftQuestionnaire(draft_id=draft.id, status=q_data["status"], answers={})
        self.db.add(quest)
        
        new_status = "QUESTIONNAIRE_PENDING" if q_data["status"] == "PENDING" else "BRIEF_READY"
        await self.repo.update_draft_status(draft.id, new_status)
        await self.db.commit()
        return draft

    async def submit_questionnaire(self, draft_id: uuid.UUID, user_id: uuid.UUID, answers: dict) -> None:
        draft = await self.repo.get_draft_by_id(draft_id)
        if not draft: raise NotFoundException("Draft not found")
        await self._verify_access(user_id, draft.matter_id)

        quest = await self.repo.get_questionnaire(draft_id)
        quest.answers = answers
        quest.status = "SUBMITTED"
        await self.repo.update_draft_status(draft_id, "BRIEF_READY")
        await self.db.commit()

    async def generate_brief_snapshot(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> MatterBriefSnapshot:
        draft = await self.repo.get_draft_by_id(draft_id)
        await self._verify_access(user_id, draft.matter_id)

        stmt = select(CaseIntelligence).where(CaseIntelligence.matter_id == draft.matter_id).order_by(CaseIntelligence.version.desc()).limit(1)
        intel = (await self.db.execute(stmt)).scalar_one_or_none()
        quest = await self.repo.get_questionnaire(draft_id)

        brief_payload = {
            "document_type": draft.document_type,
            "intelligence": intel.intelligence if intel else {},
            "questionnaire_answers": quest.answers if quest else {}
        }
        brief_hash = hashlib.sha256(json.dumps(brief_payload, sort_keys=True).encode()).hexdigest()

        snapshot = MatterBriefSnapshot(
            draft_id=draft.id,
            matter_id=draft.matter_id,
            brief=brief_payload,
            brief_hash=brief_hash,
            source_hashes={"intel_version": intel.version if intel else 0},
            created_by=user_id
        )
        await self.repo.create_brief_snapshot(snapshot)
        await self.db.commit()
        return snapshot

    async def trigger_generation(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> str:
        draft = await self.repo.get_draft_by_id(draft_id)
        if not draft: raise NotFoundException("Draft not found")
        await self._verify_access(user_id, draft.matter_id)

        if draft.status not in ["BRIEF_READY", "EDITING", "GENERATED"]:
            raise ConflictException("Draft not ready for generation")

        await self.repo.update_draft_status(draft.id, "GENERATING")
        await self.db.commit()

        job_id = f"draft_{draft.id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            await pool.enqueue_job("generate_draft", str(draft.id), _job_id=job_id, _queue_name="ai")
        return job_id

    async def finalize_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> None:
        draft = await self.repo.get_draft_by_id(draft_id)
        await self._verify_access(user_id, draft.matter_id)
        
        if draft.status == "FINALIZED":
            raise ConflictException("DRAFT_ALREADY_FINALIZED")
            
        await self.repo.update_draft_status(draft.id, "FINALIZED")
        draft.finalized_by = user_id
        draft.finalized_at = func.now()
        
        # Link the latest version as the final one
        stmt = select(DraftVersion).where(DraftVersion.draft_id == draft.id).order_by(DraftVersion.version.desc()).limit(1)
        latest_version = (await self.db.execute(stmt)).scalar_one_or_none()
        if latest_version:
            draft.final_version_id = latest_version.id
            
        await self.db.commit()

    # --- Export Methods ---

    async def request_export(self, draft_id: uuid.UUID, user_id: uuid.UUID, format: str, version_id: uuid.UUID = None) -> Tuple[uuid.UUID, str]:
        draft = await self.repo.get_draft_by_id(draft_id)
        if not draft: raise NotFoundException("Draft not found")
        await self._verify_access(user_id, draft.matter_id)

        if draft.status != "FINALIZED" and not version_id:
            raise ConflictException("Draft must be finalized before export.")

        target_version_id = version_id or draft.final_version_id
        if not target_version_id:
            raise ConflictException("No version available to export.")

        # Idempotency check: Don't spawn a new job if one exists for this version/format
        stmt = select(DraftExport).where(
            DraftExport.draft_id == draft_id,
            DraftExport.version_id == target_version_id,
            DraftExport.format == format,
            DraftExport.status.in_(["PENDING", "RENDERING", "READY"])
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing.id, "ALREADY_EXISTS"

        export = DraftExport(
            draft_id=draft_id,
            version_id=target_version_id,
            format=format,
            requested_by=user_id,
            status="PENDING"
        )
        await self.repo.create_export(export)
        await self.db.commit()

        job_id = f"exp_{export.id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            await pool.enqueue_job("export_draft", str(export.id), _job_id=job_id, _queue_name="research")

        return export.id, "ENQUEUED"

    async def get_exports(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> List[dict]:
        draft = await self.repo.get_draft_by_id(draft_id)
        await self._verify_access(user_id, draft.matter_id)

        exports = await self.repo.list_exports(draft_id)
        result = []
        for exp in exports:
            dl_url = None
            if exp.status == "READY" and exp.object_key:
                # Generate 15-minute secure pre-signed URL (§19, §D21)
                dl_url = await self.storage.generate_presigned_url(exp.object_key, expires_in=900)
            
            result.append({
                "export_id": exp.id,
                "format": exp.format,
                "status": exp.status,
                "download_url": dl_url
            })
        return result