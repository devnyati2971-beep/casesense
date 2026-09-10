"""002_document_pages_and_indexes

Revision ID: 002_document_pages
Revises: 001_initial_schema
Create Date: 2026-09-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_document_pages'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_pages table if not present
    op.execute("""
    CREATE TABLE IF NOT EXISTS document_pages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        page_number INT NOT NULL CHECK (page_number > 0),
        text TEXT NULL,
        needs_ocr BOOLEAN NOT NULL DEFAULT false,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_document_pages_doc_page UNIQUE (document_id, page_number)
    );
    """)

    # Ensure document_pages indexes exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_pages_doc_id ON document_pages(document_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_documents_matter_sha256 ON documents(matter_id, sha256);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_doc_seq ON document_chunks(document_id, seq);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_pages CASCADE;")