"""Tenant aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.shared.utils import is_valid_slug
from src.domain.tenants.events import TenantActivated, TenantCreated, TenantRenamed, TenantSuspended
from src.domain.tenants.value_objects import TenantStatus


@dataclass(eq=False, kw_only=True)
class Tenant(BaseEntity):
    name: str
    slug: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, name: str, slug: str) -> Tenant:
        clean_name = name.strip()
        clean_slug = slug.strip().lower()
        if not clean_name:
            raise InvalidOperationError("Tenant name cannot be empty")
        if not is_valid_slug(clean_slug):
            raise InvalidOperationError("Invalid slug: must be lowercase alphanumeric with hyphens, min 2 chars")
        now = datetime.now(UTC)
        tenant = cls(
            id=uuid4(),
            name=clean_name,
            slug=clean_slug,
            status=TenantStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        tenant._is_new = True
        tenant._emit(TenantCreated(tenant_id=tenant.id, name=tenant.name, slug=tenant.slug))
        return tenant

    def suspend(self) -> None:
        if self.status == TenantStatus.SUSPENDED:
            raise InvalidOperationError("Tenant is already suspended")
        self.status = TenantStatus.SUSPENDED
        self.updated_at = datetime.now(UTC)
        self._emit(TenantSuspended(tenant_id=self.id))

    def activate(self) -> None:
        if self.status == TenantStatus.ACTIVE:
            raise InvalidOperationError("Tenant is already active")
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.now(UTC)
        self._emit(TenantActivated(tenant_id=self.id))

    def rename(self, new_name: str) -> None:
        clean = new_name.strip()
        if not clean:
            raise InvalidOperationError("Tenant name cannot be empty")
        self.name = clean
        self.updated_at = datetime.now(UTC)
        self._emit(TenantRenamed(tenant_id=self.id, new_name=clean))
