import uuid
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.logging import get_logger
from app.db.engine import AsyncSessionLocal
from app.modules.drafting.models import Draft, DraftVersion, DraftSection, DraftExport
from app.modules.drafting.renderer import render_draft_to_pdf
from app.storage import get_storage_adapter

logger = get_logger(__name__)

async def generate_draft(ctx: dict, draft_id_str: str) -> None:
    """Arq background job executing drafting generation (§D10, §D23)."""
    draft_id = uuid.UUID(draft_id_str)

    async with AsyncSessionLocal() as db:
        stmt = select(Draft).where(Draft.id == draft_id)
        draft = (await db.execute(stmt)).scalar_one_or_none()
        
        if not draft:
            logger.error("Draft not found", draft_id=draft_id_str)
            return

        try:
            # 1. Simulate AI Generation Delay
            await asyncio.sleep(3)

            # 2. Persist Version
            new_version_num = draft.current_version + 1
            version = DraftVersion(
                draft_id=draft_id,
                version=new_version_num,
                source="AI",
                creation_reason="INITIAL_GENERATION"
            )
            db.add(version)
            await db.flush()

            # 3. Persist Sections (Based on DocumentType Template)
            sections_to_add = [
                DraftSection(version_id=version.id, seq=1, heading="TITLE", section_type="TITLE", body="Generated Title Block"),
                DraftSection(version_id=version.id, seq=2, heading="GROUNDS", section_type="GROUNDS", body="Generated Legal Argument linking to confirmed facts.")
            ]
            db.add_all(sections_to_add)

            # 4. Update Draft Status
            stmt_update = update(Draft).where(Draft.id == draft_id).values(
                status="GENERATED", current_version=new_version_num
            )
            await db.execute(stmt_update)
            await db.commit()
            logger.info("Draft generated successfully", draft_id=draft_id_str)

        except Exception as exc:
            logger.exception("Draft generation failed", error=str(exc))
            await db.rollback()
            await db.execute(update(Draft).where(Draft.id == draft_id).values(status="FAILED"))
            await db.commit()

async def export_draft(ctx: dict, export_id_str: str) -> None:
    """Arq background job to render PDF exports using WeasyPrint (§D21, §D23)."""
    export_id = uuid.UUID(export_id_str)
    storage = get_storage_adapter()

    async with AsyncSessionLocal() as db:
        stmt = select(DraftExport).where(DraftExport.id == export_id)
        export_job = (await db.execute(stmt)).scalar_one_or_none()
        
        if not export_job:
            logger.error("Export job not found", export_id=export_id_str)
            return

        try:
            await db.execute(update(DraftExport).where(DraftExport.id == export_id).values(status="RENDERING"))
            await db.commit()

            # Fetch Draft and Sections
            draft_stmt = select(Draft).where(Draft.id == export_job.draft_id)
            draft = (await db.execute(draft_stmt)).scalar_one_or_none()

            sec_stmt = select(DraftSection).where(
                DraftSection.version_id == export_job.version_id,
                DraftSection.status == "ACTIVE"
            ).order_by(DraftSection.seq.asc())
            sections = (await db.execute(sec_stmt)).scalars().all()

            # Prepare data for renderer
            sections_data = [{"heading": s.heading, "body": s.body} for s in sections]

            # Run WeasyPrint renderer
            pdf_bytes = render_draft_to_pdf(title=draft.title, sections_data=sections_data)

            # Upload to storage
            object_key = f"matters/{draft.matter_id}/drafts/{draft.id}/exports/{export_id}.pdf"
            await storage.put_object(key=object_key, data=pdf_bytes, content_type="application/pdf")

            # Mark READY
            await db.execute(update(DraftExport).where(DraftExport.id == export_id).values(
                status="READY", object_key=object_key
            ))
            await db.commit()
            logger.info("Draft export rendered successfully", export_id=export_id_str)

        except Exception as exc:
            logger.exception("Draft export failed", error=str(exc))
            await db.rollback()
            await db.execute(update(DraftExport).where(DraftExport.id == export_id).values(
                status="FAILED", error=str(exc)[:500]
            ))
            await db.commit()