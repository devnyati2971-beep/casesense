import io
import uuid
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.db.engine import AsyncSessionLocal
from app.modules.documents.chunker import DocumentChunker
from app.modules.documents.models import DocumentChunk, DocumentPage
from app.modules.documents.repository import DocumentRepository
from app.storage import get_storage_adapter
from app.ai.orchestrator import get_ai_orchestrator

logger = get_logger(__name__)


async def extract_text_by_pages(file_bytes: bytes, mime_type: str) -> List[Dict]:
    """Extract page text per document format."""
    pages = []
    if mime_type == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            for idx, page in enumerate(reader.pages):
                extracted = page.extract_text() or ""
                pages.append({
                    "page_number": idx + 1,
                    "text": extracted.strip(),
                    "needs_ocr": len(extracted.strip()) < 40,
                })
        except Exception as exc:
            logger.warning("pypdf parsing exception", error=str(exc))
            pages = [{"page_number": 1, "text": "", "needs_ocr": True}]
    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            full_text = "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            pages.append({"page_number": 1, "text": full_text, "needs_ocr": False})
        except Exception as exc:
            logger.warning("docx parsing error", error=str(exc))
            pages = [{"page_number": 1, "text": "", "needs_ocr": True}]
    else:
        # Plain text
        try:
            text = file_bytes.decode("utf-8", errors="replace").strip()
            pages.append({"page_number": 1, "text": text, "needs_ocr": False})
        except Exception:
            pages = [{"page_number": 1, "text": "", "needs_ocr": True}]

    return pages


async def process_document(ctx: dict, document_id_str: str) -> None:
    """Arq background job executing document extraction, chunking, and embedding."""
    document_id = uuid.UUID(document_id_str)
    storage = get_storage_adapter()
    ai_orchestrator = get_ai_orchestrator()

    async with AsyncSessionLocal() as db:
        repo = DocumentRepository(db)
        doc = await repo.get_by_id(document_id)
        if not doc:
            logger.error("Document not found during background task", document_id=document_id_str)
            return

        try:
            # Stage: PROCESSING
            await repo.update_status(document_id=document_id, status="PROCESSING")
            await db.commit()

            # Retrieve raw binary from storage
            file_bytes = await storage.get_object(doc.object_key)

            # Extract pages
            pages_data = await extract_text_by_pages(file_bytes, doc.mime_type)
            page_count = len(pages_data)

            # Persist document pages
            page_models = [
                DocumentPage(
                    document_id=document_id,
                    page_number=p["page_number"],
                    text=p["text"],
                    needs_ocr=p["needs_ocr"],
                )
                for p in pages_data
            ]
            await repo.save_pages(page_models)

            # Check if majority of pages require OCR and have zero text
            empty_pages = sum(1 for p in pages_data if len(p["text"]) == 0)
            if page_count > 0 and (empty_pages / page_count) > 0.5:
                await repo.update_status(
                    document_id=document_id,
                    status="NEEDS_REVIEW",
                    error_reason="Document appears to be a scanned PDF requiring OCR review",
                    page_count=page_count,
                )
                await db.commit()
                return

            # Paragraph-preserving chunking (§20)
            chunker = DocumentChunker()
            chunk_dicts = chunker.chunk_document_pages(pages_data)

            # Generate embeddings
            texts_to_embed = [c["text"] for c in chunk_dicts]
            embeddings = await ai_orchestrator.generate_embeddings(texts_to_embed)

            # Persist document chunks
            chunk_models = []
            for c, emb in zip(chunk_dicts, embeddings):
                chunk_models.append(
                    DocumentChunk(
                        document_id=document_id,
                        page_from=c["page_from"],
                        page_to=c["page_to"],
                        seq=c["seq"],
                        text=c["text"],
                        token_count=c["token_count"],
                        embedding=emb,
                        embedding_model="text-embedding-3-small",
                    )
                )
            await repo.save_chunks(chunk_models)

            # Finalize status to PROCESSED
            await repo.update_status(
                document_id=document_id,
                status="PROCESSED",
                page_count=page_count,
            )
            await db.commit()
            logger.info(
                "Document successfully processed",
                document_id=document_id_str,
                pages=page_count,
                chunks=len(chunk_models),
            )

        except Exception as exc:
            logger.exception("Error processing document pipeline", document_id=document_id_str, error=str(exc))
            await repo.update_status(
                document_id=document_id,
                status="FAILED",
                error_reason=str(exc)[:500],
            )
            await db.commit()