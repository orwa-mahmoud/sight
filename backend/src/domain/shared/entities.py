"""BaseEntity — shared root for all aggregates.

Provides identity, equality semantics, and per-aggregate pending event collection.
Use cases drain `pending_events` after a successful commit and dispatch via the
event bus; repositories detect insert vs. update via `is_new` / `mark_persisted`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(eq=False)
class BaseEntity:
    id: UUID
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)
    _is_new: bool = field(default=False, init=False, repr=False)

    # ── Identity-based equality ────────────────────────────────────
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    # ── Persistence detection ──────────────────────────────────────
    @property
    def is_new(self) -> bool:
        return self._is_new

    def mark_persisted(self) -> None:
        self._is_new = False

    # ── Event collection ───────────────────────────────────────────
    @property
    def pending_events(self) -> list[DomainEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    def _emit(self, event: DomainEvent) -> None:
        self._events.append(event)
