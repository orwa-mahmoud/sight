"""ListUsersForAdmin — cross-tenant user listing for the platform admin."""

from __future__ import annotations

from src.application.admin.dtos import AdminUserDTO
from src.application.shared.unit_of_work import UnitOfWork


class ListUsersForAdmin:
    """Returns every user with their (first) tenant + role context."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> list[AdminUserDTO]:
        users = await self._uow.users.list_all()
        rows: list[AdminUserDTO] = []
        for user in users:
            links = await self._uow.user_tenants.list_for_user(user.id)
            tenant_id = None
            tenant_name = None
            role = None
            if links:
                link = links[0]
                tenant_id = link.tenant_id
                role = link.role.value
                tenant = await self._uow.tenants.get_by_id(link.tenant_id)
                tenant_name = tenant.name if tenant else None
            rows.append(
                AdminUserDTO(
                    id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_platform_admin=user.is_platform_admin,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    role=role,
                )
            )
        return rows
