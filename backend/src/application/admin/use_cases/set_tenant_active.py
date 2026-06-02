"""SetTenantActive — platform admin suspends or reactivates a tenant."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import EntityNotFoundError
from src.domain.tenants.value_objects import TenantStatus


class SetTenantActive:
    """Suspend (active=False) or reactivate (active=True) a tenant. Idempotent."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: UUID, active: bool) -> str:
        tenant = await self._uow.tenants.get_by_id(tenant_id)
        if tenant is None:
            raise EntityNotFoundError("Tenant not found")

        desired = TenantStatus.ACTIVE if active else TenantStatus.SUSPENDED
        if tenant.status != desired:
            if active:
                tenant.activate()
            else:
                tenant.suspend()
            await self._uow.tenants.save(tenant)
            self._uow.track(tenant)
        return tenant.status.value
