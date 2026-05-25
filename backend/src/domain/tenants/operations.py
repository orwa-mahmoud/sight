"""Tenant operations — cross-cutting tenant management helpers."""

from __future__ import annotations

from uuid import UUID

from src.domain.shared.exceptions import EntityNotFoundError, InvalidOperationError
from src.domain.tenants.entities import Tenant
from src.domain.tenants.value_objects import TenantStatus


def ensure_active(tenant: Tenant | None, tenant_id: UUID | None = None) -> Tenant:
    """Raise if tenant is None or suspended."""
    if tenant is None:
        raise EntityNotFoundError(f"Tenant {tenant_id or 'unknown'} not found")
    if tenant.status != TenantStatus.ACTIVE:
        raise InvalidOperationError(f"Tenant {tenant.slug} is {tenant.status}")
    return tenant
