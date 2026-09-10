"""003 v2.2 lifecycle & saved citations

Revision ID: 003_v22_lifecycle
Revises: 002_document_pages
Create Date: 2026-09-09 00:00:00.000000

Additive-only (Blueprint §9 policy):
  + auth_tokens            (email verification / password reset)
  + email_outbox           (queued mail trail)
  + saved_citations        (v2.2 personal citation collection)
  + research_sessions      (blueprint §7 table that was missing)
  + research_sessions.results JSONB
  + case_intelligence.version / intelligence / ai_request_id (+ drop unique matter index)
  + authorities.session_id / proposition_id / selected_by / selected_at / note / relevance_label
  + refresh_tokens.family_id / jti
  + research_queries.session_id
  + propositions.matter_id → nullable
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003_v22_lifecycle"
down_revision = "002_document_pages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── auth_tokens (v2.1 §14.2/§14.3) ───────────────────────────────────────
    op.create_table(
        "auth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])

    # ── email_outbox (v2.1 §75.6) ────────────────────────────────────────────
    op.create_table(
        "email_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_email", sa.String(320), nullable=False),
        sa.Column("template", sa.String(40), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="QUEUED"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_resource_type", sa.String(40), nullable=True),
        sa.Column("related_resource_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_email_outbox_user_id", "email_outbox", ["user_id"])
    op.create_index("ix_email_outbox_status_created", "email_outbox", ["status", "created_at"])

    # ── saved_citations (v2.2 §7) ────────────────────────────────────────────
    op.create_table(
        "saved_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("authority_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("proposition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("propositions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("judgment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("passage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("judgment_passages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("case_name", sa.String(500), nullable=False),
        sa.Column("citation_text", sa.String(200), nullable=True),
        sa.Column("court", sa.String(200), nullable=True),
        sa.Column("decided_on", sa.Date, nullable=True),
        sa.Column("proposition_text", sa.Text, nullable=True),
        sa.Column("passage_text", sa.Text, nullable=True),
        sa.Column("location_label", sa.String(120), nullable=True),
        sa.Column("support_state", sa.String(25), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_saved_citations_user_id", "saved_citations", ["user_id"])
    op.create_index("ix_saved_citations_judgment_id", "saved_citations", ["judgment_id"])
    op.create_unique_constraint(
        "uq_saved_citations_user_judgment_passage",
        "saved_citations",
        ["user_id", "judgment_id", "passage_id"],
    )

    # ── research_sessions (blueprint §7 — table was missing) ─────────────────
    op.create_table(
        "research_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("query_text", sa.Text, nullable=True),
        sa.Column("concept_set_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="CREATED"),
        sa.Column("last_stage", sa.String(20), nullable=True),
        sa.Column("error", postgresql.JSONB, nullable=True),
        sa.Column("results", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_research_sessions_matter_id", "research_sessions", ["matter_id"])
    op.create_index("ix_research_sessions_created_by", "research_sessions", ["created_by"])

    # ── case_intelligence versioning (model alignment) ────────────────────────
    op.add_column("case_intelligence", sa.Column("version", sa.Integer(), nullable=True))
    op.add_column("case_intelligence", sa.Column("intelligence", postgresql.JSONB(), nullable=True))
    op.add_column("case_intelligence", sa.Column("ai_request_id", postgresql.UUID(as_uuid=True), nullable=True))
    # Multiple versions per matter are required (§21); drop the unique index.
    op.drop_index("ix_case_intelligence_matter_id", table_name="case_intelligence")
    op.create_index("ix_case_intelligence_matter_id", "case_intelligence", ["matter_id"])
    # Backfill existing rows with their prior columns preserved.
    op.execute(
        """
        UPDATE case_intelligence
        SET version = COALESCE(version, 1),
            intelligence = COALESCE(intelligence, jsonb_build_object(
                'summary', summary,
                'key_facts', COALESCE(key_facts, '[]'::jsonb),
                'legal_issues', COALESCE(legal_issues, '[]'::jsonb),
                'suggested_arguments', COALESCE(suggested_arguments, '[]'::jsonb)
            ))
        """
    )
    op.alter_column("case_intelligence", "version", nullable=False, server_default="1")
    op.alter_column("case_intelligence", "intelligence", nullable=False, server_default=sa.text("'{}'::jsonb"))

    # ── authorities (model alignment) ─────────────────────────────────────────
    op.add_column("authorities", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("authorities", sa.Column("proposition_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("authorities", sa.Column("selected_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("authorities", sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column("authorities", sa.Column("note", sa.Text, nullable=True))
    op.add_column("authorities", sa.Column("relevance_label", sa.String(25), nullable=True))
    op.create_index("ix_authorities_session_id", "authorities", ["session_id"])

    # ── refresh_tokens rotation semantics (§14) ───────────────────────────────
    op.add_column("refresh_tokens", sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("refresh_tokens", sa.Column("jti", sa.String(64), nullable=True))
    # Existing tokens each become their own family.
    op.execute("UPDATE refresh_tokens SET family_id = id WHERE family_id IS NULL")

    # ── research_queries.session_id (link queries to sessions) ────────────────
    op.add_column("research_queries", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))

    # ── propositions.matter_id nullable (standalone saved citations) ──────────
    op.alter_column("propositions", "matter_id", nullable=True)


def downgrade() -> None:
    op.drop_table("saved_citations")
    op.drop_table("email_outbox")
    op.drop_table("auth_tokens")
    op.drop_table("research_sessions")
    op.drop_index("ix_authorities_session_id", table_name="authorities")
    op.drop_column("authorities", "relevance_label")
    op.drop_column("authorities", "note")
    op.drop_column("authorities", "selected_at")
    op.drop_column("authorities", "selected_by")
    op.drop_column("authorities", "proposition_id")
    op.drop_column("authorities", "session_id")
    op.drop_column("refresh_tokens", "jti")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_column("research_queries", "session_id")
    op.alter_column("propositions", "matter_id", nullable=False)
    op.drop_column("case_intelligence", "ai_request_id")
    op.drop_column("case_intelligence", "intelligence")
    op.drop_column("case_intelligence", "version")
    op.drop_index("ix_case_intelligence_matter_id", table_name="case_intelligence")
    op.create_index("ix_case_intelligence_matter_id", "case_intelligence", ["matter_id"], unique=True)