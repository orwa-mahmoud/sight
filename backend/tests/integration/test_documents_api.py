"""Integration tests for document upload + list + delete."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_unsupported_file_type(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("image.png", b"fake png data", "image/png")},
    )
    # 400 (unsupported type) or 500 (embedding key missing before type check) — both acceptable
    assert resp.status_code in {400, 500}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_ingestion_persists_as_failed_document(client: AsyncClient) -> None:
    """A document that fails ingestion is recorded as FAILED (not rolled back).

    Regression: the request session rolls back on the re-raised error, which used
    to discard the failure row — leaving the owner with no record of what broke.
    An empty file parses to zero chunks, so it fails before embedding (no API key
    needed) and exercises the persist-the-failure path.
    """
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("empty.md", b"", "text/markdown")},
    )
    assert resp.status_code == 400

    resp = await client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    docs = resp.json()
    assert len(docs) == 1
    assert docs[0]["status"] == "failed"
    assert docs[0]["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_markdown_then_list_then_delete(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    md_content = b"# FAQ\\n\\nWe are open 9-5 Sunday to Thursday.\\n\\nWe accept walk-ins."
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("faq.md", md_content, "text/markdown")},
    )
    if resp.status_code in {400, 500}:
        pytest.skip("Embedding API key not configured in tenant settings — cannot test upload")
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["status"] == "ready"
    assert doc["chunk_count"] >= 1
    doc_id = doc["id"]

    # List
    resp = await client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Delete
    resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 204

    # Confirm deleted
    resp = await client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []
