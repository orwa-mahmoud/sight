"""RegisterOwner use case — atomically creates user + tenant + owner link."""

from __future__ import annotations

import re

from src.application.auth.commands import RegisterOwner
from src.application.auth.dtos import AuthResult
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.auth.ports import PasswordHasher
from src.domain.shared.exceptions import AlreadyExistsError, InvalidOperationError
from src.domain.tenants.entities import Tenant
from src.domain.users.entities import User, UserTenant
from src.domain.users.value_objects import UserTenantRole
from src.infrastructure.auth.jwt_service import JwtService

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MIN_PASSWORD_LENGTH = 8


class RegisterOwnerUseCase:
    """Create a brand-new tenant with its owner. v1 enforces 1:1 user→tenant.

    The single transaction inserts the user, tenant, and link row. If the
    email or slug is taken the caller sees `AlreadyExistsError` (HTTP 400).
    """

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

    async def execute(self, cmd: RegisterOwner) -> AuthResult:
        self._validate(cmd)

        email = cmd.email.strip().lower()
        slug = cmd.tenant_slug.strip().lower()

        if await self._uow.users.get_by_email(email):
            raise AlreadyExistsError("A user with this email already exists")
        if await self._uow.tenants.get_by_slug(slug):
            raise AlreadyExistsError("Tenant slug is already taken")

        user = User.create(
            email=email,
            hashed_password=self._password_hasher.hash(cmd.password),
            full_name=cmd.full_name,
        )
        tenant = Tenant.create(name=cmd.tenant_name, slug=slug)

        await self._uow.users.save(user)
        await self._uow.tenants.save(tenant)
        # Ensure FK targets exist before inserting the link row.
        await self._uow.flush()

        link = UserTenant.create(
            user_id=user.id,
            tenant_id=tenant.id,
            role=UserTenantRole.OWNER,
        )
        await self._uow.user_tenants.save(link)

        token = self._jwt_service.issue_access_token(user_id=user.id, tenant_id=tenant.id)
        return AuthResult(user_id=user.id, tenant_id=tenant.id, access_token=token)

    @staticmethod
    def _validate(cmd: RegisterOwner) -> None:
        if len(cmd.password) < _MIN_PASSWORD_LENGTH:
            raise InvalidOperationError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters")
        if not _SLUG_RE.match(cmd.tenant_slug.strip().lower()):
            raise InvalidOperationError("Tenant slug must contain only lowercase letters, digits, and hyphens")
        if not cmd.tenant_name.strip():
            raise InvalidOperationError("Tenant name cannot be empty")
