"""Integration tests for document list + delete use cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.documents.queries import ListDocuments, ListProcessingDocuments
from src.application.documents.use_cases.delete_document import DeleteDocumentUseCase
from src.application.documents.use_cases.list_documents import ListDocumentsUseCase
from src.application.documents.use_cases.list_processing_documents import ListProcessingDocumentsUseCase
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
async def test_list_processing_returns_only_in_flight_documents(client: None) -> None:
    """The progress endpoint surfaces uploaded/ingesting docs and hides ready ones,
    so the indicator (which polls it) re-derives in-flight work after a refresh."""
    tenant = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uploaded = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="pending.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        ingesting = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="working.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        ingesting.mark_ingesting()
        ready = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="done.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        ready.mark_ingesting()
        ready.mark_ready(chunk_count=3)
        for d in (uploaded, ingesting, ready):
            await uow.documents.save(d)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await ListProcessingDocumentsUseCase(uow=uow).execute(
            ListProcessingDocuments(tenant_id=tenant.id, active_since=datetime.now(UTC) - timedelta(hours=1))
        )
        names = {d.filename for d in result}
        assert names == {"pending.md", "working.md"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_processing_excludes_documents_stuck_past_cutoff(client: None) -> None:
    """A doc stuck in-flight past the cutoff drops out of /processing, so the UI
    stops polling it — the reaper reclaims it out of band."""
    tenant = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        fresh = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="fresh.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        stuck = Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename="stuck.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        stuck.updated_at = datetime.now(UTC) - timedelta(hours=1)
        for d in (fresh, stuck):
            await uow.documents.save(d)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await ListProcessingDocumentsUseCase(uow=uow).execute(
            ListProcessingDocuments(tenant_id=tenant.id, active_since=datetime.now(UTC) - timedelta(minutes=15))
        )
        assert {d.filename for d in result} == {"fresh.md"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_processing_isolated_by_tenant(client: None) -> None:
    tenant_a = await _make_tenant()
    tenant_b = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        d = Document.upload(
            tenant_id=tenant_a.id,
            uploaded_by_user_id=None,
            filename="a-pending.md",
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )
        await uow.documents.save(d)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await ListProcessingDocumentsUseCase(uow=uow).execute(
            ListProcessingDocuments(tenant_id=tenant_b.id, active_since=datetime.now(UTC) - timedelta(hours=1))
        )
        assert result == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_stuck_returns_only_stale_in_flight_documents(client: None) -> None:
    """The reaper reclaims documents left uploaded/ingesting past the stale window,
    across all tenants — but never fresh ones, and never already-finished ones."""
    tenant = await _make_tenant()
    old = datetime.now(UTC) - timedelta(hours=1)
    cutoff = datetime.now(UTC) - timedelta(minutes=15)

    def _doc(filename: str) -> Document:
        return Document.upload(
            tenant_id=tenant.id,
            uploaded_by_user_id=None,
            filename=filename,
            mime_type=DocumentMimeType.MARKDOWN,
            size_bytes=10,
        )

    async with async_session_factory() as session:
        uow = UnitOfWork(session)

        stale_uploaded = _doc("stale-uploaded.md")
        stale_uploaded.updated_at = old

        stale_ingesting = _doc("stale-ingesting.md")
        stale_ingesting.mark_ingesting()
        stale_ingesting.updated_at = old

        fresh_uploaded = _doc("fresh.md")  # updated just now → not yet stale

        stale_ready = _doc("done.md")  # old but finished → must be left alone
        stale_ready.mark_ingesting()
        stale_ready.mark_ready(chunk_count=2)
        stale_ready.updated_at = old

        for d in (stale_uploaded, stale_ingesting, fresh_uploaded, stale_ready):
            await uow.documents.save(d)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await uow.set_tenant_scope(tenant.id)
        stuck = await uow.documents.list_stuck_for_tenant(tenant.id, older_than=cutoff)
        assert {d.filename for d in stuck} == {"stale-uploaded.md", "stale-ingesting.md"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reaper_requeues_stuck_docs_across_all_tenants(client: None) -> None:
    """The reaper iterates every tenant under its own RLS scope, so a stuck doc in
    any tenant is re-enqueued — the fix for the fail-closed global query."""
    from unittest.mock import AsyncMock

    from src.drivers.jobs.worker import reap_stuck_documents

    old = datetime.now(UTC) - timedelta(hours=1)
    t1 = await _make_tenant()
    t2 = await _make_tenant()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        for t in (t1, t2):
            doc = Document.upload(
                tenant_id=t.id,
                uploaded_by_user_id=None,
                filename=f"stuck-{t.id}.md",
                mime_type=DocumentMimeType.MARKDOWN,
                size_bytes=10,
            )
            doc.updated_at = old
            await uow.documents.save(doc)
        await uow.commit()

    redis = AsyncMock()
    await reap_stuck_documents({"redis": redis})

    requeued_tenants = {call.args[1] for call in redis.enqueue_job.await_args_list}
    assert str(t1.id) in requeued_tenants
    assert str(t2.id) in requeued_tenants


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
