import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.logging import get_logger
from app.db.engine import get_job_session
from app.modules.research.models import ResearchSession

logger = get_logger(__name__)

async def update_session_stage(db: AsyncSession, session_id: uuid.UUID, stage: str) -> None:
    stmt = update(ResearchSession).where(ResearchSession.id == session_id).values(status=stage, last_stage=stage)
    await db.execute(stmt)
    await db.commit()


async def execute_research(ctx: dict, session_id_str: str) -> None:
    """Arq background job executing research retrieval and verification (§22, §30.2)."""
    session_id = uuid.UUID(session_id_str)

    async with get_job_session() as db:
        stmt = select(ResearchSession).where(ResearchSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        if not session:
            logger.error("Research session not found", session_id=session_id_str)
            return

        try:
            # 1. RETRIEVING
            await update_session_stage(db, session_id, "RETRIEVING")
            await asyncio.sleep(2)  # Simulating AI/Source adapter delay for UI polling

            # 2. ANALYZING
            await update_session_stage(db, session_id, "ANALYZING")
            await asyncio.sleep(2)

            # 3. VERIFYING
            await update_session_stage(db, session_id, "VERIFYING")
            await asyncio.sleep(2)

            # Generate fully compliant synthetic JSON results payload for the UI to consume.
            mock_results = {
                "groups": [
                    {
                        "issue": "Prolonged custody violates Article 21 right to speedy trial.",
                        "judgments": [
                            {
                                "judgment": {
                                    "id": str(uuid.uuid4()),
                                    "case_name": "Union of India v. K.A. Najeeb",
                                    "court": "Supreme Court of India",
                                    "decided_on": "2021-01-20",
                                    "citation": "(2021) 3 SCC 713",
                                    "source_url": "https://indiankanoon.org/doc/123456/"
                                },
                                "propositions": [
                                    {
                                        "id": str(uuid.uuid4()),
                                        "text": "Statutory restrictions under special acts do not oust the Constitutional courts' ability to grant bail on grounds of violation of Part III of the Constitution.",
                                        "relevance_label": "HIGHLY_RELEVANT",
                                        "relevance_explanation": "Directly addresses the tension between statutory bail bars and constitutional rights during prolonged incarceration.",
                                        "passages": [
                                            {
                                                "id": str(uuid.uuid4()),
                                                "text": "We are of the clear opinion that statutory restrictions like Section 43D(5) of UAPA per-se do not oust the ability of Constitutional Courts to grant bail on grounds of violation of Part III of the Constitution.",
                                                "location_label": "Para 18",
                                                "support_state": "VERIFIED"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

            # 4. COMPLETED — results persist to the dedicated `results` JSONB column.
            stmt_comp = update(ResearchSession).where(ResearchSession.id == session_id).values(
                status="COMPLETED",
                last_stage="VERIFYING",
                results=mock_results,
                error=None,
            )
            await db.execute(stmt_comp)
            await db.commit()
            logger.info("Research session completed successfully", session_id=session_id_str)

        except Exception as exc:
            logger.exception("Research execution failed", session_id=session_id_str, error=str(exc))
            stmt_fail = update(ResearchSession).where(ResearchSession.id == session_id).values(
                status="FAILED", error={"error_code": "AI_GENERATION_FAILED", "message": str(exc)}
            )
            await db.execute(stmt_fail)
            await db.commit()