"""Unit tests for BaseEntity + DomainEvent."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.domain.shared.entities import BaseEntity
from src.domain.shared.events import DomainEvent


@dataclass(eq=False, kw_only=True)
class FakeEntity(BaseEntity):
    name: str


@dataclass(frozen=True, kw_only=True)
class FakeEvent(DomainEvent):
    entity_id: UUID


def test_entity_equality_by_id() -> None:
    eid = uuid4()
    a = FakeEntity(id=eid, name="A")
    b = FakeEntity(id=eid, name="B")
    assert a == b
    assert hash(a) == hash(b)


def test_entity_inequality() -> None:
    a = FakeEntity(id=uuid4(), name="A")
    b = FakeEntity(id=uuid4(), name="A")
    assert a != b


def test_entity_not_equal_to_non_entity() -> None:
    a = FakeEntity(id=uuid4(), name="A")
    assert a != "not an entity"


def test_event_lifecycle() -> None:
    eid = uuid4()
    entity = FakeEntity(id=eid, name="X")
    assert entity.pending_events == []

    event = FakeEvent(entity_id=eid)
    entity._emit(event)
    assert len(entity.pending_events) == 1
    assert entity.pending_events[0].entity_id == eid

    entity.clear_events()
    assert entity.pending_events == []


def test_persistence_detection() -> None:
    entity = FakeEntity(id=uuid4(), name="X")
    assert not entity.is_new
    entity._is_new = True
    assert entity.is_new
    entity.mark_persisted()
    assert not entity.is_new


def test_domain_event_has_id_and_timestamp() -> None:
    event = FakeEvent(entity_id=uuid4())
    assert isinstance(event.event_id, UUID)
    assert event.occurred_at is not None
