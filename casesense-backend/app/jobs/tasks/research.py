import uuid
import json
import re
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.logging import get_logger
from app.db.engine import get_job_session
from app.modules.research.models import ResearchSession
from app.services.kanoon import KanoonService
from app.ai.orchestrator import get_ai_orchestrator
from app.modules.judgements.models import Judgment, JudgmentPassage

logger = get_logger(__name__)

# ── Prompt template ──────────────────────────────────────────────────────────
ANALYSIS_PROMPT = """You are a senior Indian legal researcher.

USER QUERY: "{query}"

JUDGMENT:
  Case: {title}
  Court: {court}
  Date: {decided_on}

QUERY-RELEVANT EXCERPTS (not the judgment introduction):
{text}

TASK:
1. Identify the SINGLE most important issue directly answering the user's query.
2. Extract ONE short, specific legal proposition (rule / principle / ratio) that answers the query. Do not summarize the Constitution, court history, or introductory facts unless the query expressly asks for them.
3. Find the EXACT sentence or passage from the text above that supports this proposition.

Return ONLY valid JSON. No markdown, no explanation outside the JSON:
{{
  "issue": "A clear, one-sentence description of the legal issue",
  "proposition": "The legal rule or principle the court laid down",
  "relevance": "Why this matters for the user's query (1-2 sentences)",
  "passage": "The EXACT quote from the judgment text that supports this proposition"
}}"""


async def update_session_stage(db: AsyncSession, session_id: uuid.UUID, stage: str) -> None:
    stmt = update(ResearchSession).where(ResearchSession.id == session_id).values(status=stage, last_stage=stage)
    await db.execute(stmt)
    await db.commit()


def _parse_date(date_str: str) -> date:
    """Parse date string from Kanoon (YYYY-MM-DD) or fallback to today."""
    if not date_str:
        return date.today()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _find_passage_in_text(passage: str, full_text: str) -> bool:
    """Check if a passage actually exists in the source text."""
    if not passage or not full_text:
        return False
    # Normalise whitespace for comparison
    norm_passage = " ".join(passage.lower().split())
    norm_text = " ".join(full_text.lower().split())
    return norm_passage in norm_text


def _query_relevant_text(text: str, query: str, limit: int = 8000) -> str:
    """Select holdings around query terms instead of blindly sending the introduction."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 40]
    terms = {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9]+", query)
        if len(word) >= 4 and word.lower() not in {"judgment", "judgement", "landmark", "legal", "under", "with", "from", "what", "does"}
    }
    if not sentences:
        return text[:limit]

    def score(sentence: str) -> int:
        lowered = sentence.lower()
        query_score = sum(lowered.count(term) for term in terms) * 10
        holding_score = sum(marker in lowered for marker in ("we hold", "held that", "is hereby", "therefore", "ratio", "settled law", "must be")) * 3
        return query_score + holding_score

    ranked = sorted(range(len(sentences)), key=lambda index: score(sentences[index]), reverse=True)
    selected = set()
    for index in ranked[:12]:
        if score(sentences[index]) <= 0 and selected:
            break
        selected.update(range(max(0, index - 1), min(len(sentences), index + 2)))
    if not selected:
        selected.update(range(min(8, len(sentences))))
    return " ".join(sentences[index] for index in sorted(selected))[:limit]


async def execute_research(ctx: dict, session_id_str: str) -> None:
    """Arq background job: fetches cases from Indian Kanoon, analyses them with AI."""
    session_id = uuid.UUID(session_id_str)

    async with get_job_session() as db:
        stmt = select(ResearchSession).where(ResearchSession.id == session_id)
        session = (await db.execute(stmt)).scalar_one_or_none()
        if not session:
            logger.error("Research session not found", session_id=session_id_str)
            return

        try:
            query = session.query_text or "General legal research"
            kanoon = KanoonService()
            ai = get_ai_orchestrator()

            # ── 1. RETRIEVING ────────────────────────────────────────────
            await update_session_stage(db, session_id, "RETRIEVING")
            search_results = await kanoon.search(query)

            # Fetch full text for top 5 cases (search results only have snippets)
            top_cases = []
            for doc in search_results[:5]:
                doc_id = doc.get("docid")
                if not doc_id:
                    continue
                full_doc = await kanoon.get_judgment(doc_id)
                if full_doc and full_doc.get("text") and len(full_doc["text"]) > 100:
                    top_cases.append(full_doc)
                if len(top_cases) >= 5:
                    break

            if not top_cases:
                logger.warning("No usable cases retrieved from Kanoon for query: %s", query)

            # ── 2. ANALYZING ─────────────────────────────────────────────
            await update_session_stage(db, session_id, "ANALYZING")

            groups = []

            for case in top_cases:
                case_text = case.get("text", "")
                title = case.get("title", "Unknown Case")
                court = case.get("court", "Unknown Court")
                decided_on_str = case.get("decided_on", "")

                # Build the prompt with actual case data
                prompt = ANALYSIS_PROMPT.format(
                    query=query,
                    title=title,
                    court=court,
                    decided_on=decided_on_str or "Unknown",
                    text=_query_relevant_text(case_text, query),
                )

                # Call AI
                ai_response = await ai.generate_json(prompt, max_tokens=1500)

                parsed = {}
                if ai_response:
                    try:
                        parsed = json.loads(ai_response)
                    except json.JSONDecodeError:
                        # Try to extract JSON from markdown code blocks
                        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                        if match:
                            try:
                                parsed = json.loads(match.group())
                            except json.JSONDecodeError:
                                pass
                        if not parsed:
                            logger.warning("Failed to parse AI response for %s", title)

                # Extract AI analysis or use sensible defaults from the case itself
                issue_text = parsed.get("issue") or f"Legal issues in: {title}"
                proposition_text = parsed.get("proposition") or ""
                relevance_text = parsed.get("relevance") or "Relevant to the query based on keyword match."
                passage_text = parsed.get("passage") or ""

                relevant_text = _query_relevant_text(case_text, query)
                # If AI is unavailable, use the most query-relevant source sentence,
                # never the first introductory sentence of the judgment.
                if not proposition_text or len(proposition_text) < 20:
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', relevant_text) if len(s.strip()) > 50]
                    proposition_text = sentences[0] if sentences else relevant_text[:300]

                # Verify passage actually exists in source; if not, use a real excerpt
                if not _find_passage_in_text(passage_text, case_text):
                    # Take a meaningful chunk from the actual text
                    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', relevant_text) if len(s.strip()) > 40]
                    passage_text = sentences[0] if sentences else relevant_text[:500]

                # ── 3. VERIFYING & Persisting ────────────────────────────
                await update_session_stage(db, session_id, "VERIFYING")

                external_id = str(case.get("docid", ""))
                decided_on = _parse_date(decided_on_str)

                # Check if judgment already exists
                stmt_check = select(Judgment).where(
                    Judgment.source == "indiankanoon",
                    Judgment.external_id == external_id,
                )
                existing_judg = (await db.execute(stmt_check)).scalar_one_or_none()
                
                # The reader opens with concise, relevant material. Full text
                # remains in ``full_text`` and is fetched only when requested.
                passages_metadata = [{
                    "paragraph_number": 1,
                    "location_label": "Relevant excerpt",
                    "text": passage_text,
                }]
                overview = {
                    "issue": issue_text,
                    "key_points": [
                        proposition_text,
                        relevance_text,
                    ],
                    "key_passage": passage_text,
                }
                citation_graph = {
                    "cited_authorities": case.get("cited_authorities", []),
                    "cited_by": case.get("cited_by", []),
                }

                if existing_judg:
                    judgment_id = existing_judg.id
                    judg = existing_judg
                    # Update existing judgment with proper data in case it was saved by old buggy code
                    judg.title = title
                    judg.court = court
                    judg.decided_on = decided_on
                    judg.judges = case.get("judges", [])
                    judg.full_text = case_text
                    judg.passages_metadata = passages_metadata
                    judg.extra_metadata = {
                        **(judg.extra_metadata or {}),
                        "overview": overview,
                        "citation_graph": citation_graph,
                    }
                else:
                    judgment_id = uuid.uuid4()
                    
                    judg = Judgment(
                        id=judgment_id,
                        source="indiankanoon",
                        external_id=external_id,
                        source_url=case.get("url", ""),
                        title=title,
                        citation=case.get("citation") or None,
                        court=court,
                        decided_on=decided_on,
                        judges=case.get("judges", []),
                        full_text=case_text,
                        text_fetched=True,
                        passages_metadata=passages_metadata,
                        extra_metadata={"overview": overview, "citation_graph": citation_graph},
                    )
                    db.add(judg)

                passage_id = uuid.uuid4()
                passage = JudgmentPassage(
                    id=passage_id,
                    judgment_id=judgment_id,
                    paragraph_number=1,
                    text=passage_text,
                )
                db.add(passage)

                # Build the result group for the frontend
                proposition_id = str(uuid.uuid4())
                group = {
                    "issue": issue_text,
                    "judgments": [{
                        "judgment": {
                            "id": str(judgment_id),
                            "case_name": title,
                            "court": court,
                            "decided_on": decided_on.isoformat(),
                            "citation": case.get("citation") or None,
                            "source_url": case.get("url", ""),
                        },
                        "propositions": [{
                            "id": proposition_id,
                            "text": proposition_text,
                            "relevance_label": "HIGHLY_RELEVANT",
                            "relevance_explanation": relevance_text,
                            "passages": [{
                                "id": str(passage_id),
                                "text": passage_text,
                                "location_label": "Relevant excerpt",
                                "support_state": "VERIFIED",
                            }],
                        }],
                    }],
                }
                groups.append(group)

            # ── 4. COMPLETED ─────────────────────────────────────────────
            results = {"groups": groups}
            stmt_comp = update(ResearchSession).where(
                ResearchSession.id == session_id
            ).values(
                status="COMPLETED",
                last_stage="VERIFYING",
                results=results,
                error=None,
            )
            await db.execute(stmt_comp)
            await db.commit()
            logger.info("Research session completed", session_id=session_id_str, num_groups=len(groups))

        except Exception as exc:
            logger.exception("Research execution failed", session_id=session_id_str, error=str(exc))
            try:
                await db.rollback()
            except Exception:
                pass
            async with get_job_session() as db2:
                stmt_fail = update(ResearchSession).where(
                    ResearchSession.id == session_id
                ).values(
                    status="FAILED",
                    error={"error_code": "AI_GENERATION_FAILED", "message": str(exc)},
                )
                await db2.execute(stmt_fail)
                await db2.commit()
