"""Tests for tenant operations."""

from __future__ import annotations

import pytest

from src.domain.shared.exceptions import EntityNotFoundError, InvalidOperationError
from src.domain.tenants.entities import Tenant
from src.domain.tenants.operations import ensure_active


def test_ensure_active_passes():
    t = Tenant.create(name="X", slug="x")
    assert ensure_active(t) is t


def test_ensure_active_none_raises():
    with pytest.raises(EntityNotFoundError):
        ensure_active(None)


def test_ensure_active_suspended_raises():
    t = Tenant.create(name="X", slug="x")
    t.suspend()
    with pytest.raises(InvalidOperationError):
        ensure_active(t)
