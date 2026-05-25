"""Outbox event repository — write + read + mark delivered."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.shared.events import DomainEvent
from src.infrastructure.persistence.postgres.models.outbox import OutboxEventModel


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def write_event(self, event: DomainEvent, tenant_id: UUID | None = None) -> None:
        data = dataclasses.asdict(event) if dataclasses.is_dataclass(event) else {}
        for k, v in data.items():
            if isinstance(v, UUID):
                data[k] = str(v)
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
        model = OutboxEventModel(
            id=uuid4(),
            event_type=type(event).__name__,
            event_data=data,
            tenant_id=str(tenant_id) if tenant_id else None,
        )
        self._session.add(model)

    async def list_pending(self, limit: int = 100) -> list[OutboxEventModel]:
        stmt = (
            select(OutboxEventModel)
            .where(OutboxEventModel.delivered.is_(False))
            .order_by(OutboxEventModel.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_delivered(self, event_id: UUID) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(delivered=True, delivered_at=datetime.now(UTC))
        )

    async def mark_failed(self, event_id: UUID, error: str) -> None:
        await self._session.execute(
            update(OutboxEventModel).where(OutboxEventModel.id == event_id).values(error=error[:2000])
        )
