"""Outbox-aware event publisher — writes events to outbox + dispatches to bus.

Call after UoW commit with the entity's pending_events. Each event is:
1. Written to the outbox_events table (at-least-once guarantee)
2. Dispatched to the in-process blinker bus (best-effort, immediate)

The outbox relay job (future Celery task) catches any events that were
written but not dispatched due to process crash.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.events import publish
from src.domain.shared.events import DomainEvent
from src.infrastructure.persistence.postgres.repositories.outbox_repo import OutboxRepository

logger = structlog.get_logger()


async def publish_events(
    events: list[DomainEvent],
    session: AsyncSession,
    tenant_id: UUID | None = None,
) -> None:
    """Write to outbox + dispatch to in-process bus."""
    if not events:
        return
    repo = OutboxRepository(session)
    for event in events:
        try:
            repo.write_event(event, tenant_id=tenant_id)
        except Exception:
            logger.warning("outbox.write_failed", event_type=type(event).__name__, exc_info=True)
    await session.commit()
    publish(events)
