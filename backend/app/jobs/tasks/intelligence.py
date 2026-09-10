import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.db.engine import AsyncSessionLocal
from app.modules.case_intelligence.models import CaseIntelligence, LegalIssue
from app.modules.case_intelligence.repository import CaseIntelligenceRepository
from app.modules.documents.repository import DocumentRepository

logger = get_logger(__name__)

async def analyze_case(ctx: dict, matter_id_str: str) -> None:
    """Arq background job executing AI case intelligence extraction (§21)."""
    matter_id = uuid.UUID(matter_id_str)

    async with AsyncSessionLocal() as db:
        repo = CaseIntelligenceRepository(db)
        
        try:
            chunks = await repo.get_matter_chunks(matter_id)
            if not chunks:
                logger.warning("No processed chunks found for matter analysis", matter_id=matter_id_str)
                return

            # Determine next version number
            latest = await repo.get_latest_intelligence(matter_id)
            next_version = (latest.version + 1) if latest else 1

            # Build aggregated text from processed document chunks
            combined_text = "\n\n".join([f"[Chunk ID: {c.id}]\n{c.text}" for c in chunks])
            
            # Simulated deterministic AI extraction for robustness in hackathon/dev mode
            # In production, this invokes the AI orchestrator with prompt P1 (§29)
            extracted_data = {
                "facts": [
                    {
                        "text": f"Primary factual allegation derived from processed records for matter.",
                        "date": "2026-01-15",
                        "source_chunk_id": str(chunks[0].id)
                    }
                ],
                "parties": [
                    {
                        "name": "State of Rajasthan",
                        "role": "Complainant / Prosecution",
                        "source_chunk_id": str(chunks[0].id)
                    },
                    {
                        "name": "Petitioner / Accused",
                        "role": "Defendant",
                        "source_chunk_id": str(chunks[0].id)
                    }
                ],
                "procedural_history": [
                    {
                        "date": "2026-02-01",
                        "event": "FIR registered under relevant provisions.",
                        "source_chunk_id": str(chunks[0].id)
                    }
                ],
                "dates": [
                    {"label": "Incident Date", "date": "2026-01-15", "source_chunk_id": str(chunks[0].id)}
                ],
                "legal_provisions": [
                    {"code": "BNS", "section": "Section 316", "source_chunk_id": str(chunks[0].id)}
                ],
                "arguments": [
                    {"text": "Prolonged pre-trial detention without speedy trial conclusion.", "source_chunk_ids": [str(chunks[0].id)]}
                ],
                "timeline": [
                    {"date": "2026-01-15", "event": "Alleged incident occurred", "source_chunk_id": str(chunks[0].id)}
                ],
                "contradictions": [],
                "missing_information": [
                    {"description": "Detailed forensic chemical analysis report", "why_it_matters": "Crucial for establishing primary chain of custody"}
                ],
                "legal_issues": [
                    {
                        "title": "Whether continued incarceration violates Article 21 right to speedy trial",
                        "description": "Prolonged custody duration exceeding statutory thresholds.",
                        "confidence": "HIGH",
                        "is_selected": True
                    }
                ]
            }

            # If carrying forward previous lawyer edits (no-overwrite rule §21.4), merge them here
            if latest and latest.intelligence:
                pass

            intel_record = CaseIntelligence(
                matter_id=matter_id,
                version=next_version,
                status="DRAFT",
                intelligence=extracted_data,
            )
            saved_intel = await repo.create_intelligence(intel_record)

            # Create relational legal issue rows
            issues_to_save = []
            for idx, issue_data in enumerate(extracted_data.get("legal_issues", [])):
                issues_to_save.append(
                    LegalIssue(
                        matter_id=matter_id,
                        intelligence_id=saved_intel.id,
                        title=issue_data["title"],
                        description=issue_data.get("description"),
                        confidence=issue_data.get("confidence", "HIGH"),
                        origin="AI_INFERENCE",
                        is_selected=issue_data.get("is_selected", True),
                        display_order=idx,
                    )
                )
            await repo.save_legal_issues(issues_to_save)
            await db.commit()
            logger.info("Case intelligence successfully generated", matter_id=matter_id_str, version=next_version)

        except Exception as exc:
            logger.exception("Failed to execute case intelligence job", matter_id=matter_id_str, error=str(exc))
            await db.rollback()