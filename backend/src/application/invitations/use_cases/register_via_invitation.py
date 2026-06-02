"""RegisterViaInvitation — a brand-new user registers through an invite link.

For invitees who don't have an account yet: create the account for the invited
email, join the tenant as STAFF, mark the invite accepted, and return an auth
token (so the route can set the session cookie, same as login/register).
"""

from __future__ import annotations

from src.application.auth.dtos import AuthResult
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.auth.ports import PasswordHasher
from src.domain.auth.ports import TokenServicePort as JwtService
from src.domain.invitations.value_objects import InvitationStatus
from src.domain.shared.exceptions import AlreadyExistsError, EntityNotFoundError, InvalidOperationError
from src.domain.users.entities import User, UserTenant
from src.domain.users.value_objects import UserTenantRole

_MIN_PASSWORD_LENGTH = 8


class RegisterViaInvitation:
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

    async def execute(self, *, token: str, password: str, full_name: str | None = None) -> AuthResult:
        invitation = await self._uow.invitations.get_by_token(token)
        if invitation is None:
            raise EntityNotFoundError("Invitation not found")
        if invitation.status != InvitationStatus.PENDING or invitation.is_expired():
            raise InvalidOperationError("Invitation is no longer valid")
        if len(password) < _MIN_PASSWORD_LENGTH:
            raise InvalidOperationError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters")
        if await self._uow.users.get_by_email(invitation.email):
            raise AlreadyExistsError("An account with this email already exists — log in to accept the invite")

        user = User.create(
            email=invitation.email,
            hashed_password=self._password_hasher.hash(password),
            full_name=full_name,
        )
        await self._uow.users.save(user)
        self._uow.track(user)
        await self._uow.flush()  # ensure the user row exists before the FK link

        link = UserTenant.create(
            user_id=user.id,
            tenant_id=invitation.tenant_id,
            role=UserTenantRole.STAFF,
        )
        await self._uow.user_tenants.save(link)
        self._uow.track(link)

        invitation.accept()
        await self._uow.invitations.save(invitation)
        self._uow.track(invitation)

        access_token = self._jwt_service.issue_access_token(user_id=user.id, tenant_id=invitation.tenant_id)
        return AuthResult(user_id=user.id, tenant_id=invitation.tenant_id, access_token=access_token)
