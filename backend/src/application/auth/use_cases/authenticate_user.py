"""AuthenticateUser use case — verify credentials and issue a token."""

from __future__ import annotations

from src.application.auth.commands import AuthenticateUser
from src.application.auth.dtos import AuthResult
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.auth.ports import PasswordHasher
from src.domain.auth.ports import TokenServicePort as JwtService
from src.domain.shared.exceptions import AuthenticationError


class AuthenticateUserUseCase:
    """Login: verify email + password, return a JWT scoped to the user's tenant."""

    def __init__(
        self,
        *,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
        jwt_service: JwtService,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._jwt_service = jwt_service

    async def execute(self, cmd: AuthenticateUser) -> AuthResult:
        # Generic message on every failure — never leaks which field was wrong.
        invalid = AuthenticationError("Invalid email or password")

        user = await self._uow.users.get_by_email(cmd.email)
        if user is None or not user.is_active:
            raise invalid

        if not self._password_hasher.verify(cmd.password, user.hashed_password):
            raise invalid

        links = await self._uow.user_tenants.list_for_user(user.id)
        if not links:
            raise AuthenticationError("User is not associated with any tenant")

        # v1: take the first (and only) tenant; v2 will let the user pick.
        tenant_id = links[0].tenant_id
        token = self._jwt_service.issue_access_token(user_id=user.id, tenant_id=tenant_id)
        return AuthResult(user_id=user.id, tenant_id=tenant_id, access_token=token)
