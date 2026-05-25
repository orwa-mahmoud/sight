"""Unit tests for outbox publisher."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.shared.outbox_publisher import publish_events
from src.domain.tenants.events import TenantCreated
from src.infrastructure.persistence.postgres.database import async_session_factory
from src.infrastructure.persistence.postgres.repositories.outbox_repo import OutboxRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_publish_events_writes_and_dispatches(client=None):
    event = TenantCreated(tenant_id=uuid4(), name="PubTest", slug="pub")
    async with async_session_factory() as session:
        await publish_events([event], session)
    # Verify written to outbox

    async with async_session_factory() as session:
        repo = OutboxRepository(session)
        pending = await repo.list_pending()
        types = [p.event_type for p in pending]
        assert "TenantCreated" in types


@pytest.mark.integration
@pytest.mark.asyncio
async def test_publish_events_empty_is_noop(client=None):
    async with async_session_factory() as session:
        await publish_events([], session)
