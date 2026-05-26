"""RefreshToken use case — issue a new JWT from user_id without re-auth."""

from __future__ import annotations

from uuid import UUID

from src.application.auth.dtos import AuthResult
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.auth.ports import TokenServicePort as JwtService
from src.domain.shared.exceptions import AuthenticationError


class RefreshTokenUseCase:
    def __init__(self, *, uow: UnitOfWork, jwt_service: JwtService) -> None:
        self._uow = uow
        self._jwt = jwt_service

    async def execute(self, user_id: UUID) -> AuthResult:
        user = await self._uow.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or disabled")
        links = await self._uow.user_tenants.list_for_user(user.id)
        if not links:
            raise AuthenticationError("No tenant")
        tenant_id = links[0].tenant_id
        token = self._jwt.issue_access_token(user_id=user.id, tenant_id=tenant_id)
        return AuthResult(user_id=user.id, tenant_id=tenant_id, access_token=token)
