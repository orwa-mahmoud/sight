"""Tests for tenant operations."""

from __future__ import annotations

import pytest

from src.domain.shared.exceptions import EntityNotFoundError, InvalidOperationError
from src.domain.tenants.entities import Tenant
from src.domain.tenants.operations import ensure_active


def test_ensure_active_passes() -> None:
    t = Tenant.create(name="X", slug="xx")
    assert ensure_active(t) is t


def test_ensure_active_none_raises() -> None:
    with pytest.raises(EntityNotFoundError):
        ensure_active(None)


def test_ensure_active_suspended_raises() -> None:
    t = Tenant.create(name="X", slug="xx")
    t.suspend()
    with pytest.raises(InvalidOperationError):
        ensure_active(t)
