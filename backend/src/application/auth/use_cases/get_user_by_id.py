"""GetUserById — resolves the authenticated user + their tenant context."""

from __future__ import annotations

from uuid import UUID

from src.application.auth.dtos import UserDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthenticationError, EntityNotFoundError


class GetUserByIdUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, user_id: UUID) -> UserDTO:
        user = await self._uow.users.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError("User not found")
        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        links = await self._uow.user_tenants.list_for_user(user.id)
        if not links:
            raise AuthenticationError("User is not associated with any tenant")
        link = links[0]

        tenant = await self._uow.tenants.get_by_id(link.tenant_id)
        if tenant is None:
            raise EntityNotFoundError("Tenant not found")

        return UserDTO(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_platform_admin=user.is_platform_admin,
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            tenant_name=tenant.name,
            role=link.role.value,
        )
