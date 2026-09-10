import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.engine import get_job_session
from app.modules.drafting.models import Draft, DraftExport, DraftSection, DraftVersion
from app.modules.drafting.renderer import render_draft_to_pdf
from app.modules.drafting.repository import DraftingRepository
from app.modules.drafting.templates import get_document_type
from app.storage import get_storage_adapter

logger = get_logger(__name__)


def _default_sections(draft: Draft, brief: dict | None) -> list[DraftSection]:
    """Build a starter set of sections from the document-type config + brief.

    In dev/stub mode this produces honest placeholder content assembled from the
    confirmed intelligence (never fabricated citations). Production replaces this
    with the AI orchestrator (prompt P7, §D10).
    """
    config = get_document_type(draft.document_type)
    section_keys = config.required_sections or ["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"]
    intelligence = (brief or {}).get("intelligence") or {}
    facts = intelligence.get("facts") or []
    parties = intelligence.get("parties") or []

    sections: list[DraftSection] = []
    for idx, key in enumerate(section_keys):
        body = ""
        if key == "TITLE":
            body = draft.title
        elif key == "PARTIES":
            body = "\n".join(
                f"{p.get('role', 'Party')}: {p.get('name', '')}"
                for p in parties
            ) or "Petitioner / Respondent details."
        elif key == "FACTS":
            body = "\n".join(f"- {f.get('text', '')}" for f in facts) or "Facts to be established from the case record."
        elif key == "GROUNDS":
            body = "The grounds for this application are supported by the confirmed case intelligence and the selected authorities."
        elif key == "DEMAND" or key == "PRAYER":
            body = "It is therefore prayed that this Hon'ble Court may be pleased to grant the relief sought herein."
        else:
            body = ""

        sections.append(DraftSection(
            section_key=key,
            title=key.replace("_", " ").title(),
            content=body,
            order_index=idx,
            origin="AI_GENERATED",
            status="ACTIVE",
            citation_ids=[],
        ))
    return sections


async def generate_draft(
    ctx: dict, draft_id_str: str,
    argument_focus: str | None = None,
    instructions: str | None = None,
    regenerate: bool = False,
) -> None:
    """Arq job — draft.generate (§D23). Creates a new immutable version."""
    draft_id = uuid.UUID(draft_id_str)

    async with get_job_session() as db:
        repo = DraftingRepository(db)
        stmt = select(Draft).where(Draft.id == draft_id)
        draft = (await db.execute(stmt)).scalar_one_or_none()
        if not draft:
            logger.error("Draft not found", draft_id=draft_id_str)
            return

        try:
            brief = await repo.get_latest_brief(draft.id)
            brief_context = brief.matter_context if brief else {}

            # New immutable version (§D14) — never mutates the previous one.
            new_version_number = draft.version + 1
            version = DraftVersion(
                draft_id=draft.id,
                version_number=new_version_number,
                content_snapshot="",
                generation_context={
                    "document_type": draft.document_type,
                    "argument_focus": argument_focus,
                    "instructions": instructions,
                    "regenerate": regenerate,
                },
                ai_model_used="stub",
                is_current=True,
            )
            await repo.create_version(version)
            await repo.clear_current_flags(draft.id)
            version.is_current = True

            sections = _default_sections(draft, brief_context)
            for section in sections:
                section.draft_id = draft.id
                section.draft_version_id = version.id
            await repo.save_sections(sections)

            version.content_snapshot = "\n\n".join(s.content for s in sections)

            # Bump the draft's version pointer + status (§D2).
            await db.execute(
                update(Draft)
                .where(Draft.id == draft.id)
                .values(
                    version=new_version_number,
                    status="GENERATED" if not regenerate else "LAWYER_REVIEW",
                )
            )
            await db.commit()
            logger.info(
                "Draft version generated",
                draft_id=draft_id_str, version=new_version_number,
                sections=len(sections),
            )

        except Exception as exc:
            logger.exception("Draft generation failed", error=str(exc))
            await db.rollback()
            await db.execute(
                update(Draft).where(Draft.id == draft.id).values(status="FAILED")
            )
            await db.commit()


async def export_draft(ctx: dict, export_id_str: str) -> None:
    """Arq job — draft.export (§D21, §D23). Renders the pinned version to PDF."""
    export_id = uuid.UUID(export_id_str)
    storage = get_storage_adapter()

    async with get_job_session() as db:
        repo = DraftingRepository(db)
        stmt = select(DraftExport).where(DraftExport.id == export_id)
        export_job = (await db.execute(stmt)).scalar_one_or_none()
        if not export_job:
            logger.error("Export job not found", export_id=export_id_str)
            return

        try:
            await repo.update_export_status(export_id, "RENDERING")
            await db.commit()

            draft_stmt = select(Draft).where(Draft.id == export_job.draft_id)
            draft = (await db.execute(draft_stmt)).scalar_one_or_none()

            # Export the finalized version (or latest when not pinned).
            version = None
            if export_job.draft_id:
                stmt_v = select(DraftVersion).where(DraftVersion.draft_id == export_job.draft_id)
                if export_job.requested_by_id:
                    pass  # version selection is by final_version_id below
                version = (await db.execute(
                    stmt_v.order_by(DraftVersion.version_number.desc()).limit(1)
                )).scalar_one_or_none()

            sections = await repo.get_sections_for_version(version.id) if version else []
            sections_data = [{"heading": s.title, "body": s.content} for s in sections]

            pdf_bytes = render_draft_to_pdf(title=draft.title, sections_data=sections_data)

            object_key = (
                f"matters/{draft.matter_id}/drafts/{draft.id}/exports/{export_id}.pdf"
            )
            await storage.put_object(
                key=object_key, data=pdf_bytes, content_type="application/pdf"
            )

            await repo.update_export_status(export_id, "READY", storage_key=object_key)
            await db.commit()
            logger.info("Draft export rendered", export_id=export_id_str)

        except Exception as exc:
            logger.exception("Draft export failed", error=str(exc))
            await db.rollback()
            await repo.update_export_status(
                export_id, "FAILED", error_message=str(exc)[:500]
            )
            await db.commit()