"""Unit tests for outbox publisher — error path (write_event failure)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.shared.outbox_publisher import publish_events
from src.domain.tenants.events import TenantCreated


@pytest.mark.asyncio
async def test_outbox_write_event_failure_is_logged_and_continues() -> None:
    """When OutboxRepository.write_event raises, the error is logged and
    the loop continues to the next event."""
    event1 = TenantCreated(tenant_id=uuid4(), name="A", slug="a")
    event2 = TenantCreated(tenant_id=uuid4(), name="B", slug="b")

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    mock_repo_instance = MagicMock()
    # First call raises, second succeeds
    mock_repo_instance.write_event = MagicMock(side_effect=[RuntimeError("DB error"), None])

    with (
        patch("src.application.shared.outbox_publisher.OutboxRepository", return_value=mock_repo_instance),
        patch("src.application.shared.outbox_publisher.publish") as mock_publish,
    ):
        await publish_events([event1, event2], mock_session)

    # Both events were attempted
    assert mock_repo_instance.write_event.call_count == 2
    # Session was committed
    mock_session.commit.assert_awaited_once()
    # Events were still dispatched to the bus
    mock_publish.assert_called_once_with([event1, event2])
