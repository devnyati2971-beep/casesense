import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AIError, ConflictException, NotFoundException, ValidationException
from app.modules.audit.service import AuditService
from app.modules.judgements.models import Judgment, JudgmentPassage
from app.modules.saved_citations.models import SavedCitation
from app.modules.saved_citations.schemas import CreateSavedCitationRequest


class SavedCitationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _chain_exists(self, model, row_id: uuid.UUID) -> bool:
        stmt = select(model.id).where(model.id == row_id)
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def create(
        self, user_id: uuid.UUID, data: CreateSavedCitationRequest
    ) -> SavedCitation:
        # Verify the referenced chain when ids are provided (§11 v2.2 contract).
        if data.authority_id and not await self._chain_exists_any("authorities", data.authority_id):
            raise ValidationException("Referenced authority does not exist.")
        if data.proposition_id and not await self._chain_exists_any("propositions", data.proposition_id):
            raise ValidationException("Referenced proposition does not exist.")
        if data.passage_id and not await self._chain_exists_any("judgment_passages", data.passage_id):
            raise ValidationException("Referenced passage does not exist.")

        judgment_id = data.judgment_id
        passage_id = data.passage_id

        # Resolve or create the judgment (deterministic dedupe by content hash).
        if judgment_id is None:
            judgment_id, _ = await self._resolve_or_create_judgment(
                case_name=data.case_name,
                citation_text=data.citation_text,
                court=data.court,
                decided_on=data.decided_on,
            )

        if passage_id is None and data.passage_text:
            passage_id = await self._resolve_or_create_passage(judgment_id, data.passage_text, data.location_label)

        # Duplicate check.
        stmt = select(SavedCitation).where(
            SavedCitation.user_id == user_id,
            SavedCitation.judgment_id == judgment_id,
            SavedCitation.passage_id == passage_id,
        )
        if (await self.db.execute(stmt)).scalar_one_or_none():
            raise ConflictException("ALREADY_SAVED: This citation is already saved.")

        saved = SavedCitation(
            user_id=user_id,
            authority_id=data.authority_id,
            proposition_id=data.proposition_id,
            judgment_id=judgment_id,
            passage_id=passage_id,
            note=data.note,
            label=data.label,
            case_name=data.case_name,
            citation_text=data.citation_text,
            court=data.court,
            decided_on=data.decided_on,
            proposition_text=data.proposition_text,
            passage_text=data.passage_text,
            location_label=data.location_label,
            support_state=data.support_state,
            # v2.2 UI fields
            citation_type=(data.citation_type or "judgment").lower(),
            tags=data.tags,
            judges=data.judges,
            category=data.category,
            related_provisions=data.related_provisions,
            summary=data.summary,
        )
        self.db.add(saved)
        await self.db.commit()
        await self.db.refresh(saved)

        await AuditService.log(
            db=self.db, user_id=user_id, action="SAVED_CITATION_ADDED",
            resource_type="SAVED_CITATION", resource_id=saved.id,
            extra_data={"judgment_id": str(judgment_id)},
        )
        return saved

    async def _chain_exists_any(self, table: str, row_id: uuid.UUID) -> bool:
        from sqlalchemy import text

        result = await self.db.execute(text(f'SELECT 1 FROM "{table}" WHERE id = :id'), {"id": row_id})
        return result.scalar_one_or_none() is not None

    async def _resolve_or_create_judgment(
        self, case_name: str, citation_text: str | None, court: str | None, decided_on
    ) -> Tuple[uuid.UUID, Judgment]:
        content_hash = hashlib.sha256(
            f"{case_name}|{citation_text or ''}|{court or ''}".encode()
        ).hexdigest()
        external_id = f"saved-{content_hash[:32]}"

        stmt = select(Judgment).where(
            Judgment.source == "MANUAL",
            Judgment.external_id == external_id,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing.id, existing

        judgment = Judgment(
            source="MANUAL",
            external_id=external_id,
            title=case_name,
            citation=citation_text,
            court=court,
            decided_on=decided_on,
            text_fetched=False,
        )
        self.db.add(judgment)
        await self.db.flush()
        return judgment.id, judgment

    async def _resolve_or_create_passage(
        self, judgment_id: uuid.UUID, passage_text: str, location_label: str | None
    ) -> uuid.UUID:
        stmt = select(JudgmentPassage).where(
            JudgmentPassage.judgment_id == judgment_id,
            JudgmentPassage.text == passage_text,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing.id

        paragraph_number = None
        if location_label and location_label.lower().startswith("para"):
            digits = "".join(ch for ch in location_label if ch.isdigit())
            if digits:
                paragraph_number = int(digits)

        passage = JudgmentPassage(
            judgment_id=judgment_id,
            paragraph_number=paragraph_number,
            text=passage_text,
        )
        self.db.add(passage)
        await self.db.flush()
        return passage.id

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        cursor: Optional[str] = None,
        citation_type: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Tuple[List[SavedCitation], Optional[str]]:
        stmt = select(SavedCitation).where(SavedCitation.user_id == user_id)
        if citation_type and citation_type.lower() != "all":
            stmt = stmt.where(SavedCitation.citation_type == citation_type.lower())
        if q:
            stmt = stmt.where(SavedCitation.case_name.ilike(f"%{q}%"))
        stmt = (
            stmt.order_by(SavedCitation.created_at.desc(), SavedCitation.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        next_cursor = str(rows[-1].id) if len(rows) > limit else None
        return rows[:limit], next_cursor

    async def counts(self, user_id: uuid.UUID) -> dict:
        """Per-type counts for the v2.2 filter chips."""
        from sqlalchemy import func

        stmt = (
            select(SavedCitation.citation_type, func.count())
            .where(SavedCitation.user_id == user_id)
            .group_by(SavedCitation.citation_type)
        )
        rows = (await self.db.execute(stmt)).all()
        by_type = {(r[0] or "other"): r[1] for r in rows}
        total = sum(by_type.values())
        return {
            "all": total,
            "judgment": by_type.get("judgment", 0),
            "act": by_type.get("act", 0),
            "article": by_type.get("article", 0),
            "other": by_type.get("other", 0),
        }

    async def _get_owned(self, user_id: uuid.UUID, citation_id: uuid.UUID) -> SavedCitation:
        stmt = select(SavedCitation).where(
            SavedCitation.id == citation_id,
            SavedCitation.user_id == user_id,
        )
        saved = (await self.db.execute(stmt)).scalar_one_or_none()
        if not saved:
            raise NotFoundException("Saved citation not found.")
        return saved

    async def get(self, user_id: uuid.UUID, citation_id: uuid.UUID) -> SavedCitation:
        return await self._get_owned(user_id, citation_id)

    async def update(
        self, user_id: uuid.UUID, citation_id: uuid.UUID, note: str | None, label: str | None
    ) -> SavedCitation:
        saved = await self._get_owned(user_id, citation_id)
        if note is not None:
            saved.note = note
        if label is not None:
            saved.label = label
        await self.db.commit()
        await self.db.refresh(saved)
        return saved

    async def translate(
        self, user_id: uuid.UUID, citation_id: uuid.UUID
    ) -> SavedCitation:
        """v2.2 translate action — Hindi rendering of the key passage.

        Uses the AI orchestrator when configured; otherwise returns the passage
        unchanged and marks the attempt. Never fabricates: translation is of
        stored source text only.
        """
        saved = await self._get_owned(user_id, citation_id)
        source_text = saved.passage_text or saved.proposition_text or saved.summary
        if not source_text:
            raise ValidationException("No passage text to translate.")

        from app.ai.orchestrator import get_ai_orchestrator

        orchestrator = get_ai_orchestrator()
        try:
            translated = await orchestrator.translate_to_hindi(source_text)
        except Exception:
            translated = None

        if translated:
            saved.translated_passage = translated
            saved.translated_at = datetime.now(timezone.utc)
        else:
            raise AIError("Translation is temporarily unavailable. Please try again.")

        await self.db.commit()
        await self.db.refresh(saved)
        return saved

    async def delete(self, user_id: uuid.UUID, citation_id: uuid.UUID) -> None:
        saved = await self._get_owned(user_id, citation_id)
        await self.db.delete(saved)
        await self.db.commit()

        await AuditService.log(
            db=self.db, user_id=user_id, action="SAVED_CITATION_REMOVED",
            resource_type="SAVED_CITATION", resource_id=citation_id,
        )
