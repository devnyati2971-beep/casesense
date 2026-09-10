import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    OptimisticLockError,
    ValidationException,
)
from app.modules.audit.service import AuditService
from app.modules.case_intelligence.models import CaseIntelligence
from app.modules.citations.models import Citation
from app.modules.drafting.models import (
    Draft,
    DraftExport,
    DraftQuestionnaire,
    DraftSection,
    DraftVersion,
    MatterBriefSnapshot,
)
from app.modules.drafting.questionnaire import AutoFillEngine
from app.modules.drafting.repository import DraftingRepository
from app.modules.drafting.templates import (
    DOCUMENT_TYPES,
    get_document_type,
    normalize_document_type,
)
from app.modules.judgements.models import Judgment, JudgmentPassage
from app.modules.matters.models import Matter
from app.storage import get_storage_adapter
from app.jobs.state import get_arq_redis

DRAFT_LIFECYCLE_STATUSES = (
    "CREATED", "QUESTIONNAIRE_PENDING", "BRIEF_READY", "GENERATING", "GENERATED",
    "LAWYER_REVIEW", "EDITING", "REGENERATING", "CITATION_REVIEW",
    "READY_FOR_FINALIZATION", "FINALIZED", "FAILED",
)


class DraftingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DraftingRepository(db)
        self.storage = get_storage_adapter()

    # ── Access control (Blueprint §15 / §D30) ─────────────────────────────────

    async def _verify_matter_access(self, user_id: uuid.UUID, matter_id: uuid.UUID) -> Matter:
        stmt = select(Matter).where(
            Matter.id == matter_id,
            Matter.owner_id == user_id,
            Matter.status != "DELETED",
        )
        matter = (await self.db.execute(stmt)).scalar_one_or_none()
        if not matter:
            raise NotFoundException("Matter not found or access denied.")
        return matter

    async def _get_draft_or_404(self, draft_id: uuid.UUID) -> Draft:
        draft = await self.repo.get_draft_by_id(draft_id)
        if not draft:
            raise NotFoundException("Draft not found.")
        return draft

    async def _get_draft_with_access(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> Draft:
        draft = await self._get_draft_or_404(draft_id)
        await self._verify_matter_access(user_id, draft.matter_id)
        return draft

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _latest_intelligence(self, matter_id: uuid.UUID) -> CaseIntelligence | None:
        stmt = (
            select(CaseIntelligence)
            .where(CaseIntelligence.matter_id == matter_id)
            .order_by(CaseIntelligence.version.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _selected_authorities(self, matter_id: uuid.UUID) -> List[dict]:
        from app.modules.authorities.models import Authority

        stmt = (
            select(Authority)
            .where(Authority.matter_id == matter_id)
            .order_by(Authority.selected_at.desc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        result = []
        for authority in rows:
            judgment = None
            if authority.judgment_id:
                jstmt = select(Judgment).where(Judgment.id == authority.judgment_id)
                judgment = (await self.db.execute(jstmt)).scalar_one_or_none()
            result.append({
                "authority_id": str(authority.id),
                "case_name": judgment.title if judgment else None,
                "citation": judgment.citation if judgment else None,
                "court": judgment.court if judgment else None,
                "relevance_label": authority.relevance_label,
            })
        return result

    # ── Draft lifecycle ────────────────────────────────────────────────────────

    async def create_draft(
        self, matter_id: uuid.UUID, user_id: uuid.UUID, doc_type: str, title: str
    ) -> Draft:
        await self._verify_matter_access(user_id, matter_id)

        canonical = normalize_document_type(doc_type)
        config = get_document_type(doc_type)
        if canonical is None or config is None:
            raise ValidationException(
                f"Invalid document_type '{doc_type}'. "
                f"Valid types: {', '.join(DOCUMENT_TYPES.keys())}"
            )

        draft = Draft(
            matter_id=matter_id,
            created_by_id=user_id,
            document_type=canonical,
            title=title or config.display_name,
            status="CREATED",
        )
        await self.repo.create_draft(draft)

        # Questionnaire is created up-front (§D6); auto-fill happens on GET.
        quest = DraftQuestionnaire(draft_id=draft.id, answers={}, is_complete=False)
        self.db.add(quest)

        new_status = "BRIEF_READY" if not config.required_info else "QUESTIONNAIRE_PENDING"
        await self.repo.update_draft_status(draft.id, new_status)
        await self.db.commit()

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=matter_id,
            action="DRAFT_CREATED", resource_type="DRAFT",
            resource_id=draft.id, extra_data={"document_type": canonical},
        )
        return draft

    async def list_drafts(self, matter_id: uuid.UUID, user_id: uuid.UUID) -> List[Draft]:
        await self._verify_matter_access(user_id, matter_id)
        return await self.repo.list_by_matter(matter_id)

    async def list_all_drafts(
        self, user_id: uuid.UUID, limit: int = 50, cursor: Optional[str] = None
    ) -> Tuple[List[dict], Optional[str]]:
        """All drafts across the user's matters (History/Drafting view, v2.2)."""
        from sqlalchemy import select

        from app.modules.matters.models import Matter

        stmt = (
            select(Draft, Matter)
            .join(Matter, Draft.matter_id == Matter.id)
            .where(Matter.owner_id == user_id)
            .order_by(Draft.updated_at.desc(), Draft.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.db.execute(stmt)).all())
        next_cursor = str(rows[-1][0].id) if len(rows) > limit else None
        items = [
            {
                "id": str(draft.id),
                "title": draft.title,
                "document_type": draft.document_type,
                "status": draft.status,
                "version": draft.version,
                "matter_id": str(draft.matter_id),
                "matter_title": matter.title,
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
            }
            for draft, matter in rows[:limit]
        ]
        return items, next_cursor

    async def get_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> Draft:
        return await self._get_draft_with_access(draft_id, user_id)

    async def get_draft_detail(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        draft = await self._get_draft_with_access(draft_id, user_id)
        latest = await self.repo.get_latest_version(draft.id)
        sections: list[DraftSection] = []
        if latest:
            sections = await self.repo.get_sections_for_version(latest.id)
        return {
            "draft": draft,
            "current_version": {
                "version": draft.version,
                "sections": sections,
                "arguments": [],
                "citations": await self._sections_citations(sections),
            },
        }

    async def _sections_citations(self, sections: List[DraftSection]) -> List[dict]:
        """Collect citations referenced by a list of sections (§26 chain)."""
        citation_ids: list[uuid.UUID] = []
        for section in sections:
            for raw in (section.citation_ids or []):
                try:
                    citation_ids.append(uuid.UUID(str(raw)))
                except ValueError:
                    continue
        if not citation_ids:
            return []
        stmt = select(Citation).where(Citation.id.in_(citation_ids))
        citations = list((await self.db.execute(stmt)).scalars().all())
        result = []
        for citation in citations:
            passage = None
            if citation.passage_id:
                pstmt = select(JudgmentPassage).where(JudgmentPassage.id == citation.passage_id)
                passage = (await self.db.execute(pstmt)).scalar_one_or_none()
            judgment = None
            if citation.judgment_id:
                jstmt = select(Judgment).where(Judgment.id == citation.judgment_id)
                judgment = (await self.db.execute(jstmt)).scalar_one_or_none()
            result.append({
                "id": str(citation.id),
                "quote": citation.quoted_text,
                "location_label": f"Para {citation.paragraph_number}" if citation.paragraph_number else None,
                "authority": {
                    "case_name": judgment.title if judgment else None,
                    "citation": judgment.citation if judgment else None,
                    "court": judgment.court if judgment else None,
                },
                "passage": {"text": passage.text if passage else None},
            })
        return result

    # ── Questionnaire (auto-fill) ──────────────────────────────────────────────

    async def get_questionnaire(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        draft = await self._get_draft_with_access(draft_id, user_id)
        quest = await self.repo.get_questionnaire(draft.id)
        intel = await self._latest_intelligence(draft.matter_id)
        matter = await self._get_matter(draft.matter_id)

        data = AutoFillEngine.generate_questionnaire(
            document_type=draft.document_type,
            intelligence=intel.intelligence if intel else {},
            matter=matter,
            existing_answers=(quest.answers if quest else {}) or {},
        )
        return {
            "status": "SUBMITTED" if (quest and quest.is_complete) else data["status"],
            "questions": data["questions"],
            "missing_required": data["missing_required"],
            "progress": data["progress"],
        }

    async def _get_matter(self, matter_id: uuid.UUID) -> dict:
        stmt = select(Matter).where(Matter.id == matter_id)
        matter = (await self.db.execute(stmt)).scalar_one_or_none()
        if not matter:
            return {}
        return {
            "court": matter.court_name,
            "court_name": matter.court_name,
            "case_number": matter.case_number,
            "client_name": matter.client_name,
            "opposite_party": matter.opposite_party,
            "title": matter.title,
        }

    async def submit_questionnaire(
        self, draft_id: uuid.UUID, user_id: uuid.UUID, answers: dict
    ) -> dict:
        draft = await self._get_draft_with_access(draft_id, user_id)
        config = get_document_type(draft.document_type)
        intel = await self._latest_intelligence(draft.matter_id)
        matter = await self._get_matter(draft.matter_id)

        merged = AutoFillEngine.generate_questionnaire(
            document_type=draft.document_type,
            intelligence=intel.intelligence if intel else {},
            matter=matter,
            existing_answers=answers,
        )
        missing = [q["field_name"] for q in merged["questions"] if q["required"] and not q["value"]]
        if missing:
            raise ValidationException(
                "Questionnaire is incomplete — required fields are missing.",
                details={"missing_required": missing},
            )

        # Persist only lawyer-provided values (auto-filled values re-derive).
        stored = {}
        for q in merged["questions"]:
            if q["field_name"] in answers:
                stored[q["field_name"]] = answers[q["field_name"]]
            elif q["auto_filled"] and q["value"] is not None:
                stored[q["field_name"]] = q["value"]

        await self.repo.save_questionnaire_answers(draft.id, stored, complete=True)
        await self.repo.update_draft_status(draft.id, "BRIEF_READY")
        await self.db.commit()

        # Snapshot the brief so generation pins what the AI saw (§D8).
        await self.generate_brief_snapshot(draft.id, user_id, commit=False)

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=draft.matter_id,
            action="QUESTIONNAIRE_SUBMITTED", resource_type="DRAFT",
            resource_id=draft.id,
            extra_data={"answered": len(stored), "missing": len(missing)},
        )
        return {"status": "BRIEF_READY", "remaining_required": []}

    # ── Matter Brief snapshot (§D8) ────────────────────────────────────────────

    async def generate_brief_snapshot(
        self, draft_id: uuid.UUID, user_id: uuid.UUID, commit: bool = True
    ) -> MatterBriefSnapshot:
        draft = await self._get_draft_with_access(draft_id, user_id)
        intel = await self._latest_intelligence(draft.matter_id)
        quest = await self.repo.get_questionnaire(draft.id)
        authorities = await self._selected_authorities(draft.matter_id)

        intelligence = intel.intelligence if intel else {}
        brief_payload = {
            "document_type": draft.document_type,
            "intelligence": intelligence,
            "questionnaire_answers": (quest.answers if quest else {}) or {},
            "selected_authorities": authorities,
        }
        brief_hash = hashlib.sha256(
            json.dumps(brief_payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        latest = await self.repo.get_latest_brief(draft.id)
        if latest and latest.matter_context and latest.matter_context.get("_brief_hash") == brief_hash:
            return latest

        snapshot = MatterBriefSnapshot(
            draft_id=draft.id,
            matter_id=draft.matter_id,
            matter_context={**brief_payload, "_brief_hash": brief_hash},
            propositions_snapshot=[],
            authorities_snapshot=authorities,
            citations_snapshot=[],
            approved=False,
        )
        await self.repo.create_brief_snapshot(snapshot)
        if commit:
            await self.db.commit()
        return snapshot

    async def get_brief(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        draft = await self._get_draft_with_access(draft_id, user_id)
        snapshot = await self.repo.get_latest_brief(draft.id)
        if not snapshot:
            snapshot = await self.generate_brief_snapshot(draft.id, user_id)
        context = snapshot.matter_context or {}
        return {
            "brief_snapshot_id": str(snapshot.id),
            "brief": {k: v for k, v in context.items() if not k.startswith("_")},
            "stale": snapshot.is_stale,
            "stale_reasons": [snapshot.stale_reason] if snapshot.stale_reason else [],
        }

    # ── Generation ─────────────────────────────────────────────────────────────

    async def trigger_generation(
        self, draft_id: uuid.UUID, user_id: uuid.UUID, argument_focus: str | None = None
    ) -> str:
        draft = await self._get_draft_with_access(draft_id, user_id)

        if draft.status in ("FINALIZED",):
            raise ConflictException("FINALIZED_IMMUTABLE: Finalized drafts cannot be regenerated via generate.")
        if draft.status in ("GENERATING", "REGENERATING"):
            raise ConflictException("GENERATION_IN_PROGRESS")

        if draft.status in ("CREATED", "QUESTIONNAIRE_PENDING"):
            # §D22 gating: a brief must exist before generation.
            raise ConflictException(
                "QUESTIONNAIRE_INCOMPLETE: Complete the questionnaire to generate this draft."
            )

        # Ensure a brief snapshot is pinned.
        await self.generate_brief_snapshot(draft.id, user_id, commit=True)

        await self.repo.update_draft_status(draft.id, "GENERATING")
        await self.db.commit()

        job_id = f"draft_{draft.id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            await pool.enqueue_job(
                "generate_draft", str(draft.id),
                _job_id=job_id,
                argument_focus=argument_focus,
            )
        return job_id

    async def regenerate_draft(
        self, draft_id: uuid.UUID, user_id: uuid.UUID, instructions: str | None = None
    ) -> str:
        draft = await self._get_draft_with_access(draft_id, user_id)
        if draft.status == "FINALIZED":
            raise ConflictException("FINALIZED_IMMUTABLE")
        if draft.status in ("GENERATING", "REGENERATING"):
            raise ConflictException("GENERATION_IN_PROGRESS")

        await self.repo.update_draft_status(draft.id, "REGENERATING")
        await self.db.commit()

        job_id = f"draft_{draft.id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            await pool.enqueue_job(
                "generate_draft", str(draft.id),
                _job_id=job_id,
                instructions=instructions,
                regenerate=True,
            )
        return job_id

    # ── Editing (PATCH with optimistic lock §D29) ─────────────────────────────

    async def patch_draft(
        self,
        draft_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
        sections: List[dict] | None = None,
        title: str | None = None,
    ) -> Draft:
        draft = await self._get_draft_with_access(draft_id, user_id)
        if draft.status == "FINALIZED":
            raise ConflictException("FINALIZED_IMMUTABLE")

        fields: dict[str, Any] = {}
        if title is not None:
            fields["title"] = title
        if sections is not None:
            latest = await self.repo.get_latest_version(draft.id)
            if not latest:
                raise ConflictException("No generated version exists to edit yet.")
            section_map = {
                str(s.id): s for s in await self.repo.get_sections_for_version(latest.id)
            }
            for item in sections:
                section_id = item.get("id")
                if not section_id or str(section_id) not in section_map:
                    continue
                await self.repo.update_section_content(
                    str(section_id),
                    content=item.get("content", ""),
                    title=item.get("title"),
                )
            fields["status"] = "EDITING"

        updated = await self.repo.update_draft(
            draft.id, expected_version, **fields
        )
        if updated is None:
            raise OptimisticLockError()
        await self.db.commit()

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=draft.matter_id,
            action="DRAFT_EDITED", resource_type="DRAFT",
            resource_id=draft.id, extra_data={"version": updated.version},
        )
        return updated

    # ── Versions ───────────────────────────────────────────────────────────────

    async def list_versions(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> List[dict]:
        draft = await self._get_draft_with_access(draft_id, user_id)
        versions = await self.repo.list_versions(draft.id)
        return [
            {
                "version": v.version_number,
                "source": "AI" if v.ai_model_used else "LAWYER",
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "is_final": draft.final_version_id == v.id,
                "is_current": v.is_current,
            }
            for v in versions
        ]

    # ── Finalization (§D19 gate) ───────────────────────────────────────────────

    async def _validate_finalization(self, draft: Draft) -> None:
        blocking: list[dict] = []
        config = get_document_type(draft.document_type)

        quest = await self.repo.get_questionnaire(draft.id)
        if not (quest and quest.is_complete):
            blocking.append({"code": "QUESTIONNAIRE_INCOMPLETE", "detail": "Required questionnaire answers are missing."})

        latest = await self.repo.get_latest_version(draft.id)
        if not latest:
            blocking.append({"code": "NO_VERSION", "detail": "No generated version exists."})

        if config and config.required_sections:
            sections = await self.repo.get_sections_for_version(latest.id) if latest else []
            present = {s.section_key for s in sections}
            missing_sections = [s for s in config.required_sections if s not in present]
            if missing_sections:
                blocking.append({"code": "REQUIRED_SECTIONS_MISSING", "detail": str(missing_sections)})
            empty = [s.section_key for s in sections if not (s.content or "").strip()]
            if empty:
                blocking.append({"code": "EMPTY_SECTION", "detail": str(empty)})

        if blocking:
            raise ValidationException(
                "Draft cannot be finalized — blocking checks failed.",
                details={"blocking": blocking},
            )

    async def finalize_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> Draft:
        draft = await self._get_draft_with_access(draft_id, user_id)
        if draft.status == "FINALIZED":
            raise ConflictException("DRAFT_ALREADY_FINALIZED")

        await self._validate_finalization(draft)

        latest = await self.repo.get_latest_version(draft.id)
        updated = await self.repo.update_draft(
            draft.id,
            expected_version=draft.version,
            status="FINALIZED",
            finalized_by_id=user_id,
            finalized_at=datetime.now(tz=timezone.utc).isoformat(),
            final_version_id=latest.id if latest else None,
        )
        if updated is None:
            raise OptimisticLockError()
        await self.db.commit()

        await AuditService.log(
            db=self.db, user_id=user_id, matter_id=draft.matter_id,
            action="DRAFT_FINALIZED", resource_type="DRAFT",
            resource_id=draft.id,
            extra_data={"final_version_id": str(latest.id) if latest else None},
        )
        return updated

    # ── Traceability (§D33) ────────────────────────────────────────────────────

    async def traceability(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        draft = await self._get_draft_with_access(draft_id, user_id)
        latest = await self.repo.get_latest_version(draft.id)
        sections = await self.repo.get_sections_for_version(latest.id) if latest else []

        arguments: List[dict] = []
        for section in sections:
            citations = await self._section_citation_chain(section)
            arguments.append({
                "text": section.content,
                "section": section.section_key,
                "propositions": citations,
            })
        return {"arguments": arguments}

    async def _section_citation_chain(self, section: DraftSection) -> List[dict]:
        citation_ids = []
        for raw in (section.citation_ids or []):
            try:
                citation_ids.append(uuid.UUID(str(raw)))
            except ValueError:
                continue
        if not citation_ids:
            return []
        stmt = select(Citation).where(Citation.id.in_(citation_ids))
        citations = list((await self.db.execute(stmt)).scalars().all())
        chain: List[dict] = []
        for citation in citations:
            passage = None
            if citation.passage_id:
                pstmt = select(JudgmentPassage).where(JudgmentPassage.id == citation.passage_id)
                passage = (await self.db.execute(pstmt)).scalar_one_or_none()
            judgment = None
            if citation.judgment_id:
                jstmt = select(Judgment).where(Judgment.id == citation.judgment_id)
                judgment = (await self.db.execute(jstmt)).scalar_one_or_none()
            chain.append({
                "text": citation.quoted_text,
                "authorities": [{
                    "case_name": judgment.title if judgment else "Unknown case",
                    "citation": judgment.citation,
                    "court": judgment.court,
                    "source_url": judgment.source_url,
                    "passages": [{
                        "text": passage.text if passage else None,
                        "location_label": f"Para {passage.paragraph_number}" if passage and passage.paragraph_number else None,
                    }] if passage else [],
                }] if judgment else [],
            })
        return chain

    # ── Export (§D21) ──────────────────────────────────────────────────────────

    async def request_export(
        self, draft_id: uuid.UUID, user_id: uuid.UUID, format: str, version_id: uuid.UUID | None = None
    ) -> Tuple[uuid.UUID, str]:
        draft = await self._get_draft_with_access(draft_id, user_id)
        if format.lower() not in ("pdf", "docx"):
            raise ValidationException("Unsupported export format — must be 'pdf' or 'docx'.")

        target_version_id = version_id or draft.final_version_id
        if not target_version_id:
            raise ConflictException("Draft must be finalized before export.")

        # Idempotency: reuse an existing in-flight/READY export for (draft, version, format).
        stmt = select(DraftExport).where(
            DraftExport.draft_id == draft.id,
            DraftExport.format == format.lower(),
            DraftExport.status.in_(["PENDING", "RENDERING", "READY"]),
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing.id, "ALREADY_EXISTS"

        export = DraftExport(
            draft_id=draft.id,
            format=format.lower(),
            status="PENDING",
            requested_by_id=user_id,
        )
        await self.repo.create_export(export)
        await self.db.commit()

        job_id = f"exp_{export.id}_{uuid.uuid4().hex[:8]}"
        pool = await get_arq_redis()
        if pool:
            await pool.enqueue_job(
                "export_draft", str(export.id),
                _job_id=job_id,
            )
        return export.id, "ENQUEUED"

    async def get_exports(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> List[dict]:
        draft = await self._get_draft_with_access(draft_id, user_id)
        exports = await self.repo.list_exports(draft.id)
        result = []
        for exp in exports:
            download_url = None
            if exp.status == "READY" and exp.storage_key:
                download_url = await self.storage.generate_presigned_url(exp.storage_key, expires_in=900)
            result.append({
                "export_id": str(exp.id),
                "format": exp.format,
                "status": exp.status,
                "download_url": download_url,
            })
        return result

    async def get_validation(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        draft = await self._get_draft_with_access(draft_id, user_id)
        blocking: list[dict] = []
        warnings: list[dict] = []
        config = get_document_type(draft.document_type)

        quest = await self.repo.get_questionnaire(draft.id)
        if not (quest and quest.is_complete):
            blocking.append({"code": "QUESTIONNAIRE_INCOMPLETE", "detail": "Required questionnaire answers are missing."})

        latest = await self.repo.get_latest_version(draft.id)
        if not latest:
            blocking.append({"code": "NO_VERSION", "detail": "No generated version exists."})
        elif config and config.required_sections:
            sections = await self.repo.get_sections_for_version(latest.id)
            present = {s.section_key for s in sections}
            for section in config.required_sections:
                if section not in present:
                    blocking.append({"code": "REQUIRED_SECTIONS_MISSING", "detail": f"Missing section: {section}"})
        if draft.status == "FINALIZED":
            blocking.append({"code": "FINALIZED", "detail": "Draft is already finalized."})

        return {
            "ready": not blocking,
            "blocking": blocking,
            "warnings": warnings,
        }