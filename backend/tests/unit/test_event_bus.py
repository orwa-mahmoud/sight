"""Unit tests for the blinker event bus."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.bootstrap.events import clear_all, publish, subscribe
from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class FakeEvent(DomainEvent):
    entity_id: UUID


def test_subscribe_and_publish() -> None:
    clear_all()
    received: list[FakeEvent] = []

    def handler(event: DomainEvent) -> None:
        assert isinstance(event, FakeEvent)
        received.append(event)

    subscribe(FakeEvent, handler)
    event = FakeEvent(entity_id=uuid4())
    publish([event])

    assert len(received) == 1
    assert received[0].entity_id == event.entity_id


def test_publish_no_subscribers() -> None:
    clear_all()
    event = FakeEvent(entity_id=uuid4())
    publish([event])  # no crash


def test_handler_error_is_isolated() -> None:
    clear_all()
    call_count = 0

    def failing_handler(event: DomainEvent) -> None:
        raise RuntimeError("I broke")

    def counting_handler(event: DomainEvent) -> None:
        nonlocal call_count
        call_count += 1

    subscribe(FakeEvent, failing_handler)
    subscribe(FakeEvent, counting_handler)

    event = FakeEvent(entity_id=uuid4())
    publish([event])

    # counting_handler should still have been called despite failing_handler
    assert call_count == 1


def test_multiple_events_dispatched() -> None:
    clear_all()
    received: list[UUID] = []

    def handler(event: DomainEvent) -> None:
        assert isinstance(event, FakeEvent)
        received.append(event.entity_id)

    subscribe(FakeEvent, handler)
    events = [FakeEvent(entity_id=uuid4()) for _ in range(3)]
    publish(events)

    assert len(received) == 3


def test_clear_all_removes_subscriptions() -> None:
    clear_all()
    received: list[FakeEvent] = []

    def handler(event: DomainEvent) -> None:
        assert isinstance(event, FakeEvent)
        received.append(event)

    subscribe(FakeEvent, handler)
    clear_all()

    publish([FakeEvent(entity_id=uuid4())])
    assert len(received) == 0
