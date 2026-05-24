"""DomainEvent — base for everything emitted by aggregates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events.

    Subclasses add their own typed fields. `kw_only=True` so subclasses can
    declare required fields without ordering errors against the defaulted
    `event_id` / `occurred_at` here.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
