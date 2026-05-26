"""Unit tests for event collector."""

from __future__ import annotations

from src.application.shared.event_collector import collect_events
from src.domain.tenants.entities import Tenant


def test_collect_events_drains() -> None:
    t1 = Tenant.create(name="A", slug="aa")
    t2 = Tenant.create(name="B", slug="bb")
    events = collect_events(t1, t2)
    assert len(events) == 2
    assert t1.pending_events == []
    assert t2.pending_events == []


def test_collect_events_empty() -> None:
    events = collect_events()
    assert events == []
