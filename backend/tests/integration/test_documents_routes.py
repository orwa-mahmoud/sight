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


@pytest.mark.asyncio
async def test_bulk_delete_removes_only_own_documents_in_one_request(client: AsyncClient) -> None:
    from uuid import UUID, uuid4

    from src.application.shared.unit_of_work import UnitOfWork
    from src.domain.documents.entities import Document
    from src.domain.documents.value_objects import DocumentMimeType
    from src.domain.tenants.entities import Tenant
    from src.infrastructure.persistence.postgres.database import async_session_factory

    token, _, tenant_id = await register_and_token(client)

    def _doc(tid: UUID, name: str) -> Document:
        return Document.upload(
            tenant_id=tid, uploaded_by_user_id=None, filename=name, mime_type=DocumentMimeType.MARKDOWN, size_bytes=10
        )

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        mine = [_doc(UUID(tenant_id), f"mine-{i}.md") for i in range(3)]
        other_tenant = Tenant.create(name="Other", slug=f"other-{uuid4().hex[:8]}")
        await uow.tenants.save(other_tenant)
        await uow.flush()
        foreign = _doc(other_tenant.id, "foreign.md")
        for d in [*mine, foreign]:
            await uow.documents.save(d)
        await uow.commit()

    # One request with a mix of my ids, a foreign id, and a random id.
    resp = await client.post(
        "/api/v1/documents/bulk-delete",
        headers={"Authorization": f"Bearer {token}"},
        json={"ids": [str(mine[0].id), str(mine[1].id), str(mine[2].id), str(foreign.id), str(uuid4())]},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 3  # only my three, not the foreign/random ids

    # My docs are gone; the other tenant's doc is untouched.
    remaining = await client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert remaining.json() == []
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        assert await uow.documents.get_by_id(foreign.id) is not None
