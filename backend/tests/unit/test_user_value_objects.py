"""Unit tests for user value objects."""

from __future__ import annotations

from src.domain.users.value_objects import UserTenantRole


def test_user_tenant_role_values() -> None:
    assert UserTenantRole.OWNER == "owner"
    assert UserTenantRole.STAFF == "staff"
