"""Unit tests for tenant value objects."""

from __future__ import annotations

from src.domain.tenants.value_objects import TenantStatus


def test_tenant_status_values() -> None:
    assert TenantStatus.ACTIVE == "active"
    assert TenantStatus.SUSPENDED == "suspended"
