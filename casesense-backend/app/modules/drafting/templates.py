"""
Document type configuration — Blueprint §D4, §D5.

Each document type is configuration, not code: adding a type = adding one
config object. The identifiers below are the canonical §D4 set (v2.2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class QuestionSpec:
    question_id: str
    field_name: str
    field_type: Literal["TEXT", "LONG_TEXT", "DATE", "INT", "ENUM", "BOOL"]
    required: bool
    source: str = "ANSWER"  # MATTER | INTELLIGENCE | DOCUMENT | ANSWER
    options: list[str] | None = None
    label: str = ""


@dataclass(frozen=True)
class DocumentTypeConfig:
    id: str
    display_name: str
    purpose: str
    required_info: list[str] = field(default_factory=list)
    optional_info: list[str] = field(default_factory=list)
    questionnaire: list[QuestionSpec] = field(default_factory=list)
    required_sections: list[str] = field(default_factory=list)
    optional_sections: list[str] = field(default_factory=list)
    relevant_intelligence: list[str] = field(default_factory=list)
    required_authorities: int = 0
    section_order: list[str] = field(default_factory=list)

    @property
    def questionnaire_summary(self) -> list[str]:
        return [q.question_id for q in self.questionnaire]


# ── Type definitions ──────────────────────────────────────────────────────────

BAIL_APPLICATION = DocumentTypeConfig(
    id="BAIL_APPLICATION",
    display_name="Bail Application",
    purpose="Application for regular bail before the trial court or High Court.",
    required_info=[
        "accused_name", "fir_number", "police_station", "offence_sections",
        "custody_duration", "grounds_for_release", "court",
    ],
    optional_info=[
        "previous_applications", "chargesheet_filed", "co_accused_status",
        "surety_details", "trial_status", "client_ref",
    ],
    questionnaire=[
        QuestionSpec("accused_name", "accused_name", "TEXT", True, "INTELLIGENCE", label="Accused / Petitioner name"),
        QuestionSpec("fir_number", "fir_number", "TEXT", True, "INTELLIGENCE", label="FIR Number"),
        QuestionSpec("police_station", "police_station", "TEXT", True, "INTELLIGENCE", label="Police Station"),
        QuestionSpec("offence_sections", "offence_sections", "TEXT", True, "INTELLIGENCE", label="Offence sections (e.g. BNS 316)"),
        QuestionSpec("custody_duration", "custody_duration", "TEXT", True, "ANSWER", label="Custody duration so far"),
        QuestionSpec("grounds_for_release", "grounds_for_release", "LONG_TEXT", True, "ANSWER", label="Grounds for release"),
        QuestionSpec("court", "court", "TEXT", True, "MATTER", label="Court"),
        QuestionSpec("chargesheet_filed", "chargesheet_filed", "BOOL", False, "ANSWER", label="Has a chargesheet been filed?"),
        QuestionSpec("previous_applications", "previous_applications", "TEXT", False, "ANSWER", label="Previous bail applications"),
    ],
    required_sections=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
    optional_sections=["PROCEDURAL_HISTORY", "LEGAL_ISSUES", "VERIFICATION", "ANNEXURES"],
    relevant_intelligence=["facts", "parties", "procedural_history", "legal_provisions", "timeline"],
    required_authorities=2,
    section_order=["TITLE", "PARTIES", "FACTS", "PROCEDURAL_HISTORY", "GROUNDS", "PRAYER", "VERIFICATION"],
)

LEGAL_NOTICE = DocumentTypeConfig(
    id="LEGAL_NOTICE",
    display_name="Legal Notice",
    purpose="Formal notice sent on behalf of the client before litigation.",
    required_info=["client_name", "opposite_party", "subject", "demand", "deadline", "court"],
    questionnaire=[
        QuestionSpec("client_name", "client_name", "TEXT", True, "MATTER", label="Client name"),
        QuestionSpec("opposite_party", "opposite_party", "TEXT", True, "MATTER", label="Opposite party"),
        QuestionSpec("subject", "subject", "TEXT", True, "ANSWER", label="Subject of notice"),
        QuestionSpec("demand", "demand", "LONG_TEXT", True, "ANSWER", label="Relief / demand"),
        QuestionSpec("deadline", "deadline", "TEXT", False, "ANSWER", label="Deadline for compliance"),
        QuestionSpec("court", "court", "TEXT", False, "MATTER", label="Court (if applicable)"),
    ],
    required_sections=["TITLE", "PARTIES", "FACTS", "DEMAND", "PRAYER"],
    optional_sections=["VERIFICATION", "ANNEXURES"],
    relevant_intelligence=["facts", "parties", "legal_provisions", "timeline"],
    section_order=["TITLE", "PARTIES", "FACTS", "DEMAND", "PRAYER", "VERIFICATION"],
)

CUSTOM = DocumentTypeConfig(
    id="CUSTOM",
    display_name="Custom Document",
    purpose="Free-form document with editable sections.",
    questionnaire=[],
    required_sections=[],
    optional_sections=[],
    relevant_intelligence=["facts", "parties", "legal_provisions"],
    section_order=["TITLE", "PARTIES", "FACTS", "OTHER"],
)

# ── Registry (blueprint §D4: all 10 types represented) ───────────────────────

DOCUMENT_TYPES: dict[str, DocumentTypeConfig] = {
    "BAIL_APPLICATION": BAIL_APPLICATION,
    "LEGAL_NOTICE": LEGAL_NOTICE,
    "REPLY_LEGAL_NOTICE": DocumentTypeConfig(
        id="REPLY_LEGAL_NOTICE",
        display_name="Reply to Legal Notice",
        purpose="Response to a received legal notice.",
        required_info=["client_name", "opposite_party", "subject"],
        questionnaire=[
            QuestionSpec("client_name", "client_name", "TEXT", True, "MATTER", label="Client name"),
            QuestionSpec("opposite_party", "opposite_party", "TEXT", True, "MATTER", label="Sender of notice"),
            QuestionSpec("subject", "subject", "TEXT", True, "ANSWER", label="Subject"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
        section_order=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
    ),
    "COMPLAINT": DocumentTypeConfig(
        id="COMPLAINT",
        display_name="Complaint",
        purpose="Initiates legal proceedings before a court or forum.",
        required_info=["complainant", "opposite_party", "relief"],
        questionnaire=[
            QuestionSpec("complainant", "complainant", "TEXT", True, "MATTER", label="Complainant"),
            QuestionSpec("opposite_party", "opposite_party", "TEXT", True, "MATTER", label="Opposite party"),
            QuestionSpec("relief", "relief", "LONG_TEXT", True, "ANSWER", label="Relief sought"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
        section_order=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
    ),
    "WRITTEN_STATEMENT": DocumentTypeConfig(
        id="WRITTEN_STATEMENT",
        display_name="Written Statement",
        purpose="Respondent's statement of defence.",
        required_info=["respondent", "case_number", "court"],
        questionnaire=[
            QuestionSpec("respondent", "respondent", "TEXT", True, "MATTER", label="Respondent"),
            QuestionSpec("case_number", "case_number", "TEXT", True, "MATTER", label="Case number"),
            QuestionSpec("court", "court", "TEXT", True, "MATTER", label="Court"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
        section_order=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
    ),
    "REPRESENTATION": DocumentTypeConfig(
        id="REPRESENTATION",
        display_name="Representation",
        purpose="Representation to an authority or department.",
        required_info=["applicant", "subject"],
        questionnaire=[
            QuestionSpec("applicant", "applicant", "TEXT", True, "MATTER", label="Applicant"),
            QuestionSpec("subject", "subject", "TEXT", True, "ANSWER", label="Subject"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "PRAYER"],
        section_order=["TITLE", "PARTIES", "FACTS", "PRAYER"],
    ),
    "RTI_APPLICATION": DocumentTypeConfig(
        id="RTI_APPLICATION",
        display_name="RTI Application",
        purpose="Application under the Right to Information Act, 2005.",
        required_info=["applicant", "information_sought"],
        questionnaire=[
            QuestionSpec("applicant", "applicant", "TEXT", True, "MATTER", label="Applicant"),
            QuestionSpec("information_sought", "information_sought", "LONG_TEXT", True, "ANSWER", label="Information sought"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "PRAYER"],
        section_order=["TITLE", "PARTIES", "FACTS", "PRAYER"],
    ),
    "CONSUMER_COMPLAINT": DocumentTypeConfig(
        id="CONSUMER_COMPLAINT",
        display_name="Consumer Complaint",
        purpose="Complaint before a Consumer Commission.",
        required_info=["complainant", "opposite_party", "relief"],
        questionnaire=[
            QuestionSpec("complainant", "complainant", "TEXT", True, "MATTER", label="Complainant"),
            QuestionSpec("opposite_party", "opposite_party", "TEXT", True, "MATTER", label="Opposite party"),
            QuestionSpec("relief", "relief", "LONG_TEXT", True, "ANSWER", label="Relief sought"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
        section_order=["TITLE", "PARTIES", "FACTS", "GROUNDS", "PRAYER"],
    ),
    "CONTRACT_CLAUSES": DocumentTypeConfig(
        id="CONTRACT_CLAUSES",
        display_name="Contract Clauses",
        purpose="Drafting a set of contract clauses.",
        required_info=["parties", "purpose"],
        questionnaire=[
            QuestionSpec("parties", "parties", "TEXT", True, "MATTER", label="Parties"),
            QuestionSpec("purpose", "purpose", "LONG_TEXT", True, "ANSWER", label="Purpose of contract"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS"],
        section_order=["TITLE", "PARTIES", "FACTS"],
    ),
    "AFFIDAVIT": DocumentTypeConfig(
        id="AFFIDAVIT",
        display_name="Affidavit",
        purpose="First-person sworn statement.",
        required_info=["deponent", "statement"],
        questionnaire=[
            QuestionSpec("deponent", "deponent", "TEXT", True, "MATTER", label="Deponent"),
            QuestionSpec("statement", "statement", "LONG_TEXT", True, "ANSWER", label="Statement"),
        ],
        required_sections=["TITLE", "PARTIES", "FACTS", "VERIFICATION"],
        section_order=["TITLE", "PARTIES", "FACTS", "VERIFICATION"],
    ),
    "CUSTOM": CUSTOM,
}

# Legacy v1 identifiers → canonical §D4 identifiers (F4 §71.2).
_LEGACY_TYPE_ALIASES = {
    "bail_application": "BAIL_APPLICATION",
    "bail": "BAIL_APPLICATION",
    "legal_notice": "LEGAL_NOTICE",
    "reply": "REPLY_LEGAL_NOTICE",
    "written_statement": "WRITTEN_STATEMENT",
    "written_submission": "WRITTEN_STATEMENT",
    "complaint": "COMPLAINT",
    "plaint": "COMPLAINT",
    "representation": "REPRESENTATION",
    "rti_application": "RTI_APPLICATION",
    "consumer_complaint": "CONSUMER_COMPLAINT",
    "contract_clauses": "CONTRACT_CLAUSES",
    "affidavit": "AFFIDAVIT",
    "custom": "CUSTOM",
}


def normalize_document_type(doc_type: str) -> str | None:
    """Accept both canonical §D4 ids and legacy ids; return canonical id or None."""
    key = (doc_type or "").strip().upper()
    if key in DOCUMENT_TYPES:
        return key
    return _LEGACY_TYPE_ALIASES.get(key.lower())


def get_document_type(doc_type: str) -> DocumentTypeConfig | None:
    canonical = normalize_document_type(doc_type)
    return DOCUMENT_TYPES.get(canonical) if canonical else None