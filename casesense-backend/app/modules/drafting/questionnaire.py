"""
Questionnaire generation + auto-fill — Blueprint §D6, §D7.

The system never re-asks for information the Matter already has. Resolution is
deterministic (no LLM): explicit lawyer answers win, then matter columns, then
case-intelligence items matching the declared source hint.

Auto-filled values always carry their source; lawyer-provided answers are never
overwritten by later auto-fill runs.
"""

from __future__ import annotations

import re
from typing import Any

from app.modules.drafting.templates import DocumentTypeConfig, get_document_type

ORIGIN_ANSWER = "LAWYER_PROVIDED"
ORIGIN_AUTO_FILL = "AUTO_FILL"


def _first_text(items: list[dict] | None, key: str = "text") -> str | None:
    if not items:
        return None
    for item in items:
        value = item.get(key)
        if value:
            return str(value)
    return None


def _match_party(intelligence: dict, role_hints: tuple[str, ...]) -> str | None:
    parties = intelligence.get("parties") or []
    for party in parties:
        role = str(party.get("role", "")).lower()
        if any(hint in role for hint in role_hints):
            return str(party.get("name"))
    return None


def _match_procedural_event(intelligence: dict, pattern: str) -> str | None:
    history = intelligence.get("procedural_history") or []
    for event in history:
        text = str(event.get("event", ""))
        if re.search(pattern, text, re.IGNORECASE):
            return text
    return None


def _match_provision(intelligence: dict) -> str | None:
    provisions = intelligence.get("legal_provisions") or []
    for prov in provisions:
        code = prov.get("code", "")
        section = prov.get("section", "")
        if code or section:
            return f"{code} {section}".strip()
    return None


class AutoFillEngine:
    """Deterministic mapping from Matter + Case Intelligence → questionnaire values."""

    # field_name → resolver signature
    _RESOLVERS: dict[str, Any] = {
        "court": lambda m, i: (m or {}).get("court") or (m or {}).get("court_name"),
        "case_number": lambda m, i: (m or {}).get("case_number"),
        "client_name": lambda m, i: (m or {}).get("client_name"),
        "client_ref": lambda m, i: (m or {}).get("client_ref"),
        "complainant": lambda m, i: _match_party(i, ("complainant", "prosecution", "state")) or (m or {}).get("client_name"),
        "accused_name": lambda m, i: _match_party(i, ("accused", "petitioner", "defendant")),
        "petitioner": lambda m, i: _match_party(i, ("petitioner", "accused", "defendant")),
        "respondent": lambda m, i: _match_party(i, ("respondent", "complainant", "prosecution")) or (m or {}).get("opposite_party"),
        "opposite_party": lambda m, i: (m or {}).get("opposite_party"),
        "deponent": lambda m, i: _match_party(i, ("petitioner", "accused")) or (m or {}).get("client_name"),
        "applicant": lambda m, i: (m or {}).get("client_name") or _match_party(i, ("petitioner", "accused")),
        "fir_number": lambda m, i: _match_procedural_event(i, r"fir|first information report"),
        "police_station": lambda m, i: _match_procedural_event(i, r"police station"),
        "offence_sections": lambda m, i: _match_provision(i),
    }

    @classmethod
    def _resolve_field(cls, field_name: str, matter: dict, intelligence: dict) -> str | None:
        resolver = cls._RESOLVERS.get(field_name)
        if resolver is None:
            return None
        value = resolver(matter or {}, intelligence or {})
        if isinstance(value, bool):
            return "yes" if value else "no"
        if value is None:
            return None
        return str(value).strip() or None

    @classmethod
    def generate_questionnaire(
        cls,
        document_type: str,
        intelligence: dict | None = None,
        matter: dict | None = None,
        existing_answers: dict | None = None,
    ) -> dict:
        """
        Returns:
        {
          "status": "PENDING" | "SUBMITTED",
          "questions": [ {question_id, field_name, field_type, required, source,
                          auto_filled, value, options, label} ],
          "missing_required": [field_name, ...],
          "progress": 0..100
        }
        """
        config = get_document_type(document_type)
        intelligence = intelligence or {}
        matter = matter or {}
        existing_answers = existing_answers or {}

        questions: list[dict] = []
        missing_required: list[str] = []

        for spec in (config.questionnaire if config else []):
            auto_value: str | None = None
            source_hint = spec.source
            # 1. Explicit lawyer answer always wins (§D7 immutability)
            if spec.field_name in existing_answers:
                value = existing_answers[spec.field_name]
                origin = ORIGIN_ANSWER
                source_hint = "ANSWER"
            else:
                # 2. Deterministic auto-fill from matter + intelligence
                auto_value = cls._resolve_field(spec.field_name, matter, intelligence)
                if auto_value:
                    value = auto_value
                    origin = ORIGIN_AUTO_FILL
                else:
                    value = None
                    origin = ORIGIN_ANSWER
                    if spec.required:
                        missing_required.append(spec.field_name)

            questions.append({
                "question_id": spec.question_id,
                "field_name": spec.field_name,
                "field_type": spec.field_type,
                "required": spec.required,
                "source": source_hint,
                "auto_filled": origin == ORIGIN_AUTO_FILL,
                "value": value,
                "options": spec.options,
                "label": spec.label or spec.question_id.replace("_", " ").title(),
            })

        answered = sum(1 for q in questions if q["value"])
        total = len(questions)
        progress = int((answered / total) * 100) if total else 100
        status = "SUBMITTED" if not missing_required else "PENDING"

        return {
            "status": status,
            "questions": questions,
            "missing_required": missing_required,
            "progress": progress,
        }