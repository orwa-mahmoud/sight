"""Unit tests for key facts entities."""

from __future__ import annotations

from uuid import uuid4

from src.domain.key_facts.entities import KeyFact


def test_key_fact_create() -> None:
    f = KeyFact.create(tenant_id=uuid4(), contact_id=uuid4(), key="  Name  ", value="  Sara  ")
    assert f.is_new
    assert f.key == "name"
    assert f.value == "Sara"


def test_key_fact_update_value() -> None:
    f = KeyFact.create(tenant_id=uuid4(), contact_id=uuid4(), key="language", value="English")
    f.update_value("  Arabic  ")
    assert f.value == "Arabic"
