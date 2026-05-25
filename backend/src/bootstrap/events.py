"""Blinker-based event bus — fire-and-forget domain event dispatch.

Domain events emitted by entities (via `_emit()`) are collected by the
UoW and published here after a successful commit. Handlers subscribe
per-event-type and execute side effects (send notifications, update
caches, invalidate circuit breakers, etc.).

Handler isolation: each handler runs in its own try/except so one failing
handler doesn't prevent others from executing. Errors are logged but
never propagated to the caller — the primary transaction already committed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from blinker import Namespace

from src.domain.shared.events import DomainEvent

logger = structlog.get_logger()

_signals = Namespace()


def subscribe(event_type: type[DomainEvent], handler: Callable[[DomainEvent], Any]) -> None:
    """Register a handler for a specific domain event type."""
    signal = _signals.signal(event_type.__name__)
    signal.connect(handler, weak=False)


def publish(events: list[DomainEvent]) -> None:
    """Dispatch a list of domain events to their subscribers.

    Called by the route/use-case layer AFTER the UoW commits.
    Each handler is isolated — failures are logged, not raised.
    """
    for event in events:
        signal = _signals.signal(type(event).__name__)
        for handler_ref in signal.receivers_for(event):
            try:
                handler_ref(event)
            except Exception:
                logger.error(
                    "event_bus.handler_failed",
                    event_type=type(event).__name__,
                    event_id=str(event.event_id),
                    exc_info=True,
                )


def clear_all() -> None:
    """Remove all subscriptions. Used in tests."""
    for name in list(_signals):
        _signals.signal(name).receivers.clear()
