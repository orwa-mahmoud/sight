"""Outbox event model — transactional outbox for domain events.

Intended pattern: events are written in the same transaction as the entity
change; a relay job (polling or Celery beat) reads pending rows, publishes
them to the event bus, then marks them delivered.

NOTE: This table is a ready-to-use component (exercised by
`tests/unit/test_outbox_repo.py`) but is NOT yet wired into the commit path.
Today the Unit of Work dispatches domain events synchronously in-process via
the blinker bus (`bootstrap/events.py`) after each commit. Wiring the outbox
in would make dispatch durable across process crashes — see the backlog.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.postgres.models import Base


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
