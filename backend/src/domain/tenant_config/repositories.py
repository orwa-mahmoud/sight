"""TenantConfig repository port."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.tenant_config.entities import TenantConfig


class TenantConfigRepository(Protocol):
    async def save(self, config: TenantConfig) -> None: ...

    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantConfig | None: ...
