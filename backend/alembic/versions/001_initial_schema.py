"""Initial schema — all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-01 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable required PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgvector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="advocate"),
        sa.Column("bar_council_id", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"])

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ── matters ───────────────────────────────────────────────────────────────
    op.create_table(
        "matters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("matter_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("court_name", sa.String(500), nullable=True),
        sa.Column("case_number", sa.String(200), nullable=True),
        sa.Column("client_name", sa.String(500), nullable=True),
        sa.Column("opposite_party", sa.String(500), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_matters_owner_id", "matters", ["owner_id"])
    op.create_index("ix_matters_id", "matters", ["id"])

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploader_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("mime_type", sa.String(200), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("processing_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_matter_id", "documents", ["matter_id"])
    op.create_index("ix_documents_storage_key", "documents", ["storage_key"], unique=True)

    # ── document_chunks ───────────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("chunk_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_matter_id", "document_chunks", ["matter_id"])

    # ── case_intelligence ─────────────────────────────────────────────────────
    op.create_table(
        "case_intelligence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("key_facts", postgresql.JSONB, nullable=True),
        sa.Column("legal_issues", postgresql.JSONB, nullable=True),
        sa.Column("suggested_arguments", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("job_id", sa.String(255), nullable=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_case_intelligence_matter_id", "case_intelligence", ["matter_id"], unique=True)

    # ── propositions ──────────────────────────────────────────────────────────
    op.create_table(
        "propositions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("intelligence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("case_intelligence.id", ondelete="SET NULL"), nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("confirmed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ai_confidence", sa.Float, nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_propositions_matter_id", "propositions", ["matter_id"])
    op.create_index("ix_propositions_intelligence_id", "propositions", ["intelligence_id"])

    # ── judgments ─────────────────────────────────────────────────────────────
    op.create_table(
        "judgments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source", sa.String(50), nullable=False, server_default="indiankanoon"),
        sa.Column("external_id", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("citation", sa.String(500), nullable=True),
        sa.Column("court", sa.String(500), nullable=True),
        sa.Column("court_level", sa.String(50), nullable=True),
        sa.Column("decided_on", sa.Date, nullable=True),
        sa.Column("judges", postgresql.JSONB, nullable=True),
        sa.Column("subject_matter", sa.String(500), nullable=True),
        sa.Column("full_text", sa.Text, nullable=True),
        sa.Column("text_fetched", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("passages_metadata", postgresql.JSONB, nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_judgments_external_id", "judgments", ["external_id"])
    op.create_index("ix_judgments_citation", "judgments", ["citation"])
    op.create_unique_constraint("uq_judgments_source_external_id", "judgments", ["source", "external_id"])

    # ── judgment_passages ─────────────────────────────────────────────────────
    op.create_table(
        "judgment_passages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("judgment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paragraph_number", sa.Integer, nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("passage_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_judgment_passages_judgment_id", "judgment_passages", ["judgment_id"])

    # ── research_queries ──────────────────────────────────────────────────────
    op.create_table(
        "research_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("initiated_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("propositions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("job_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("search_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_research_queries_matter_id", "research_queries", ["matter_id"])

    # ── research_results ──────────────────────────────────────────────────────
    op.create_table(
        "research_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("judgment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=True),
        sa.Column("relevance_explanation", sa.Text, nullable=True),
        sa.Column("rank", sa.Integer, nullable=True),
        sa.Column("selected_by_lawyer", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_research_results_query_id", "research_results", ["query_id"])

    # ── citations ─────────────────────────────────────────────────────────────
    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("propositions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("judgment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("passage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgment_passages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quoted_text", sa.Text, nullable=True),
        sa.Column("paragraph_number", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="unverified"),
        sa.Column("verification_method", sa.String(50), nullable=True),
        sa.Column("verified_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("verification_notes", sa.Text, nullable=True),
        sa.Column("added_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_ai_suggested", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_citations_matter_id", "citations", ["matter_id"])
    op.create_index("ix_citations_judgment_id", "citations", ["judgment_id"])

    # ── authorities ───────────────────────────────────────────────────────────
    op.create_table(
        "authorities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("judgment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("confirmed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_authorities_matter_id", "authorities", ["matter_id"])

    # ── drafts ────────────────────────────────────────────────────────────────
    op.create_table(
        "drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("final_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("final_content_snapshot", sa.Text, nullable=True),
        sa.Column("finalized_at", sa.String(50), nullable=True),
        sa.Column("finalized_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drafts_matter_id", "drafts", ["matter_id"])

    # ── draft_versions ────────────────────────────────────────────────────────
    op.create_table(
        "draft_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content_snapshot", sa.Text, nullable=True),
        sa.Column("generation_context", postgresql.JSONB, nullable=True),
        sa.Column("ai_model_used", sa.String(100), nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_draft_versions_draft_id", "draft_versions", ["draft_id"])

    # ── draft_sections ────────────────────────────────────────────────────────
    op.create_table(
        "draft_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("draft_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("draft_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("section_key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("origin", sa.String(50), nullable=False, server_default="ai_generated"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("pending_regeneration_content", sa.Text, nullable=True),
        sa.Column("ai_instructions", sa.Text, nullable=True),
        sa.Column("citation_ids", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_draft_sections_draft_id", "draft_sections", ["draft_id"])

    # ── draft_questionnaires ──────────────────────────────────────────────────
    op.create_table(
        "draft_questionnaires",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answers", postgresql.JSONB, nullable=True),
        sa.Column("schema_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("is_complete", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_draft_questionnaires_draft_id", "draft_questionnaires", ["draft_id"], unique=True)

    # ── matter_brief_snapshots ────────────────────────────────────────────────
    op.create_table(
        "matter_brief_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matter_context", postgresql.JSONB, nullable=True),
        sa.Column("propositions_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("authorities_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("citations_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("stale_reason", sa.Text, nullable=True),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_matter_brief_snapshots_draft_id", "matter_brief_snapshots", ["draft_id"])

    # ── draft_exports ─────────────────────────────────────────────────────────
    op.create_table(
        "draft_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drafts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("storage_key", sa.String(1000), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_draft_exports_draft_id", "draft_exports", ["draft_id"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_matter_id", "audit_logs", ["matter_id"])

    # ── pgvector HNSW indexes for similarity search ────────────────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_judgment_passages_embedding_hnsw
        ON judgment_passages USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_judgments_embedding_hnsw
        ON judgments USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("draft_exports")
    op.drop_table("matter_brief_snapshots")
    op.drop_table("draft_questionnaires")
    op.drop_table("draft_sections")
    op.drop_table("draft_versions")
    op.drop_table("drafts")
    op.drop_table("authorities")
    op.drop_table("citations")
    op.drop_table("research_results")
    op.drop_table("research_queries")
    op.drop_table("judgment_passages")
    op.drop_table("judgments")
    op.drop_table("propositions")
    op.drop_table("case_intelligence")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("matters")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pgvector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')