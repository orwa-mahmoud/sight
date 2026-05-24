"""DomainEvent — base for everything emitted by aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    Subclasses add their own typed fields. The base provides identity (event_id)
    and a UTC timestamp so the outbox / event bus can dedupe and order events.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
