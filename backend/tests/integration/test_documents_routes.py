"""Integration tests for the documents routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_upload_document_no_filename(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("", b"content", "application/octet-stream")},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_documents_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/documents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.delete(
        "/api/v1/documents/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (404, 204)
