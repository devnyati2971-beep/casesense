"""
Shared enumerations used across all modules.
These mirror the PostgreSQL CHECK constraints and blueprint §7 exactly.
"""

from __future__ import annotations

import enum


# ── User ──────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADVOCATE = "advocate"
    ADMIN = "admin"


# ── Matter ────────────────────────────────────────────────────────────────────

class MatterStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"


class MatterType(str, enum.Enum):
    CIVIL = "civil"
    CRIMINAL = "criminal"
    CONSTITUTIONAL = "constitutional"
    ARBITRATION = "arbitration"
    TRIBUNAL = "tribunal"
    OTHER = "other"


# ── Document ──────────────────────────────────────────────────────────────────

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    FIR = "fir"
    COMPLAINT = "complaint"
    ORDER = "order"
    PLEADING = "pleading"
    NOTICE = "notice"
    JUDGMENT = "judgment"
    AFFIDAVIT = "affidavit"
    CONTRACT = "contract"
    EVIDENCE = "evidence"
    OTHER = "other"


# ── Case Intelligence ─────────────────────────────────────────────────────────

class IntelligenceStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PropositionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


# ── Research ──────────────────────────────────────────────────────────────────

class ResearchStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Judgment / Legal Source ───────────────────────────────────────────────────

class JudgmentSource(str, enum.Enum):
    INDIANKANOON = "indiankanoon"
    MANUAL = "manual"
    STUB = "stub"


class CourtLevel(str, enum.Enum):
    SUPREME_COURT = "supreme_court"
    HIGH_COURT = "high_court"
    DISTRICT_COURT = "district_court"
    TRIBUNAL = "tribunal"
    OTHER = "other"


# ── Citation ──────────────────────────────────────────────────────────────────

class CitationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class CitationVerificationMethod(str, enum.Enum):
    EXACT_MATCH = "exact_match"
    SEMANTIC_MATCH = "semantic_match"
    MANUAL = "manual"


# ── Authority ─────────────────────────────────────────────────────────────────

class AuthorityStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


# ── Draft / Drafting ──────────────────────────────────────────────────────────

class DraftStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"


class DraftDocumentType(str, enum.Enum):
    """10 document types supported by the drafting engine (§D4)."""
    WRITTEN_SUBMISSION = "written_submission"
    BAIL_APPLICATION = "bail_application"
    WRIT_PETITION = "writ_petition"
    APPEAL = "appeal"
    REPLY = "reply"
    REJOINDER = "rejoinder"
    LEGAL_NOTICE = "legal_notice"
    PLAINT = "plaint"
    WRITTEN_STATEMENT = "written_statement"
    SYNOPSIS = "synopsis"


class DraftSectionOrigin(str, enum.Enum):
    AI_GENERATED = "ai_generated"
    LAWYER_EDITED = "lawyer_edited"
    REGENERATED = "regenerated"
    SUPERSEDED = "superseded"


class DraftSectionStatus(str, enum.Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    PENDING_REVIEW = "pending_review"


class DraftExportFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


class DraftExportStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Background Jobs ───────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditAction(str, enum.Enum):
    # Auth
    USER_REGISTERED = "user.registered"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    TOKEN_REFRESHED = "token.refreshed"
    # Matter
    MATTER_CREATED = "matter.created"
    MATTER_UPDATED = "matter.updated"
    MATTER_ARCHIVED = "matter.archived"
    # Document
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    DOCUMENT_DELETED = "document.deleted"
    # Intelligence
    INTELLIGENCE_GENERATED = "intelligence.generated"
    PROPOSITION_CONFIRMED = "proposition.confirmed"
    PROPOSITION_REJECTED = "proposition.rejected"
    # Research
    RESEARCH_INITIATED = "research.initiated"
    RESEARCH_COMPLETED = "research.completed"
    # Citation
    CITATION_ADDED = "citation.added"
    CITATION_VERIFIED = "citation.verified"
    CITATION_REJECTED = "citation.rejected"
    # Authority
    AUTHORITY_CONFIRMED = "authority.confirmed"
    AUTHORITY_REJECTED = "authority.rejected"
    # Draft
    DRAFT_CREATED = "draft.created"
    DRAFT_GENERATED = "draft.generated"
    DRAFT_SECTION_EDITED = "draft.section_edited"
    DRAFT_SECTION_REGENERATED = "draft.section_regenerated"
    DRAFT_FINALIZED = "draft.finalized"
    DRAFT_EXPORTED = "draft.exported"