import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from app.jobs.tasks.document import process_document
from app.modules.documents.repository import DocumentRepository


def make_pdf(text: str = "Mock Legal Notice Document Content with paragraphs\n\nSecond paragraph for case.") -> bytes:
    """Build a minimal but valid one-page PDF containing `text`."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    content = DecodedStreamObject()
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(content)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_and_list_documents(client: AsyncClient):
    # 1. Register and login
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "lawyer_doc@casesense.in",
            "password": "Password123!",
            "full_name": "Advocate Sharma",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create matter
    matter_res = await client.post(
        "/api/v1/matters",
        headers=headers,
        json={"title": "State v. Ramesh Kumar", "case_number": "BAIL/2026/104"},
    )
    assert matter_res.status_code == 201
    matter_id = matter_res.json()["data"]["id"]

    # 3. Upload Document
    pdf_content = make_pdf()
    files = {"file": ("bail_application.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_res = await client.post(
        f"/api/v1/matters/{matter_id}/documents",
        headers=headers,
        files=files,
    )
    assert upload_res.status_code == 202
    data = upload_res.json()
    assert data["document"]["file_name"] == "bail_application.pdf"
    assert data["document"]["status"] == "UPLOADED"
    doc_id = data["document"]["id"]

    # 4. Duplicate upload check (409 Conflict)
    dup_files = {"file": ("bail_application.pdf", io.BytesIO(pdf_content), "application/pdf")}
    dup_res = await client.post(
        f"/api/v1/matters/{matter_id}/documents",
        headers=headers,
        files=dup_files,
    )
    assert dup_res.status_code == 409

    # 5. List documents
    list_res = await client.get(f"/api/v1/matters/{matter_id}/documents", headers=headers)
    assert list_res.status_code == 200
    docs = list_res.json()["items"]
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id

    # 6. Status check
    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "UPLOADED"

    # 7. Execute document pipeline task directly
    await process_document({}, str(doc_id))

    # Verify status transitioned to PROCESSED
    post_status = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert post_status.status_code == 200
    assert post_status.json()["status"] == "PROCESSED"

    # 8. Soft delete document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 204

    # Document should now be excluded from active list
    relist_res = await client.get(f"/api/v1/matters/{matter_id}/documents", headers=headers)
    assert relist_res.status_code == 200
    assert len(relist_res.json()["items"]) == 0


@pytest.mark.asyncio
async def test_document_matter_isolation(client: AsyncClient):
    # Register User A
    user_a_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "user_a@casesense.in", "password": "Password123!", "full_name": "Advocate A"},
    )
    token_a = user_a_res.json()["data"]["tokens"]["access_token"]

    # Register User B
    user_b_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "user_b@casesense.in", "password": "Password123!", "full_name": "Advocate B"},
    )
    token_b = user_b_res.json()["data"]["tokens"]["access_token"]

    # User A creates matter
    matter_a = await client.post(
        "/api/v1/matters",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"title": "Matter User A"},
    )
    matter_a_id = matter_a.json()["data"]["id"]

    # User B tries to upload to User A's matter -> 404 NOT_FOUND (existence hidden)
    pdf_content = b"%PDF-1.4 Foreign Matter Test Content"
    files = {"file": ("unauthorized.pdf", io.BytesIO(pdf_content), "application/pdf")}
    unauth_upload = await client.post(
        f"/api/v1/matters/{matter_a_id}/documents",
        headers={"Authorization": f"Bearer {token_b}"},
        files=files,
    )
    assert unauth_upload.status_code == 404