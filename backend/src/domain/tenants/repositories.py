"""Tenant repository port — implementations live in infrastructure."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.tenants.entities import Tenant


class TenantRepository(Protocol):
    async def save(self, tenant: Tenant) -> None: ...

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None: ...

    async def get_by_slug(self, slug: str) -> Tenant | None: ...

    async def list_all(self) -> list[Tenant]: ...
