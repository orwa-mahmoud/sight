"""Integration tests for outbox repository."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.tenants.events import TenantCreated
from src.infrastructure.persistence.postgres.database import async_session_factory
from src.infrastructure.persistence.postgres.repositories.outbox_repo import OutboxRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_and_list_pending(client=None):
    async with async_session_factory() as session:
        repo = OutboxRepository(session)
        event = TenantCreated(tenant_id=uuid4(), name="Test", slug="test")
        await repo.write_event(event, tenant_id=uuid4())
        await session.commit()
    async with async_session_factory() as session:
        repo = OutboxRepository(session)
        pending = await repo.list_pending()
        assert len(pending) >= 1
        assert pending[0].event_type == "TenantCreated"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mark_delivered(client=None):
    async with async_session_factory() as session:
        repo = OutboxRepository(session)
        event = TenantCreated(tenant_id=uuid4(), name="Del", slug="del")
        await repo.write_event(event)
        await session.commit()
    async with async_session_factory() as session:
        repo = OutboxRepository(session)
        pending = await repo.list_pending()
        await repo.mark_delivered(pending[0].id)
        await session.commit()
    async with async_session_factory() as session:
        repo = OutboxRepository(session)
        pending = await repo.list_pending()
        delivered_ids = {p.id for p in pending}
        # The delivered one should not be in pending
