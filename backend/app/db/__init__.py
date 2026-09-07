# Ensure all models are imported so SQLAlchemy metadata registers them
from app.modules.users.models import User
from app.modules.matters.models import Matter
from app.modules.documents.models import Document, DocumentChunk
from app.modules.case_intelligence.models import CaseIntelligence, Proposition
from app.modules.research.models import ResearchQuery, ResearchResult
# from app.modules.judgements.models import Judgment
from app.modules.citations.models import Citation
from app.modules.authorities.models import Authority
from app.modules.drafting.models import (
    Draft,
    DraftVersion,
    DraftSection,
    DraftQuestionnaire,
    MatterBriefSnapshot,
    DraftExport,
)
from app.modules.audit.models import AuditLog

__all__ = [
    "User",
    "Matter",
    "Document",
    "DocumentChunk",
    "CaseIntelligence",
    "Proposition",
    "ResearchQuery",
    "ResearchResult",
    "Judgment",
    "Citation",
    "Authority",
    "Draft",
    "DraftVersion",
    "DraftSection",
    "DraftQuestionnaire",
    "MatterBriefSnapshot",
    "DraftExport",
    "AuditLog",
]
