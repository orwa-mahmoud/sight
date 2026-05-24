"""Integration tests for document list + delete use cases."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.documents.queries import ListDocuments
from src.application.documents.use_cases.list_documents import DeleteDocumentUseCase, ListDocumentsUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory


async def _make_tenant() -> Tenant:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="Doc Test", slug=f"dt-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.commit()
        return tenant


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_documents_empty(client: None) -> None:
    tenant = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await ListDocumentsUseCase(uow=uow).execute(ListDocuments(tenant_id=tenant.id))
        assert result == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_documents_with_entries(client: None) -> None:
    tenant = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        d = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="a.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        await uow.documents.save(d)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await ListDocumentsUseCase(uow=uow).execute(ListDocuments(tenant_id=tenant.id))
        assert len(result) == 1
        assert result[0].filename == "a.md"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_document_success(client: None) -> None:
    tenant = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        d = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="b.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        await uow.documents.save(d)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await DeleteDocumentUseCase(uow=uow).execute(tenant_id=tenant.id, document_id=d.id)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        assert await uow.documents.get_by_id(d.id) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_document_not_found(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        with pytest.raises(EntityNotFoundError):
            await DeleteDocumentUseCase(uow=uow).execute(tenant_id=uuid4(), document_id=uuid4())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_document_wrong_tenant(client: None) -> None:
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        d = Document.upload(
            tenant_id=tenant_a.id,
            uploaded_by_user_id=None,
            filename="c.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        await uow.documents.save(d)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        with pytest.raises(AuthorizationError):
            await DeleteDocumentUseCase(uow=uow).execute(tenant_id=tenant_b.id, document_id=d.id)
