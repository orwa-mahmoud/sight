"""User + UserTenant aggregates.

`User` is the login identity (email + hashed password).
`UserTenant` is the join row giving a user access to a tenant with a role.
A user can later belong to multiple tenants; v1 enforces 1:1 at the use-case level.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.users.events import (
    PlatformAdminGranted,
    PlatformAdminRevoked,
    UserAddedToTenant,
    UserRegistered,
)
from src.domain.users.value_objects import UserTenantRole


@dataclass(eq=False, kw_only=True)
class User(BaseEntity):
    email: str
    hashed_password: str
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, email: str, hashed_password: str, full_name: str | None = None) -> User:
        now = datetime.now(UTC)
        user = cls(
            id=uuid4(),
            email=email.strip().lower(),
            hashed_password=hashed_password,
            full_name=full_name.strip() if full_name else None,
            is_active=True,
            is_platform_admin=False,
            created_at=now,
            updated_at=now,
        )
        user._is_new = True
        user._emit(UserRegistered(user_id=user.id, email=user.email))
        return user

    def deactivate(self) -> None:
        if self.is_platform_admin:
            raise InvalidOperationError("Platform admins cannot be deactivated")
        if not self.is_active:
            raise InvalidOperationError("User is already deactivated")
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        if self.is_active:
            raise InvalidOperationError("User is already active")
        self.is_active = True
        self.updated_at = datetime.now(UTC)

    def grant_platform_admin(self) -> None:
        """Promote to platform super-admin. Idempotent: a no-op if already one."""
        if self.is_platform_admin:
            return
        self.is_platform_admin = True
        self.updated_at = datetime.now(UTC)
        self._emit(PlatformAdminGranted(user_id=self.id, email=self.email))

    def revoke_platform_admin(self) -> None:
        """Demote from platform super-admin. Idempotent: a no-op if not one."""
        if not self.is_platform_admin:
            return
        self.is_platform_admin = False
        self.updated_at = datetime.now(UTC)
        self._emit(PlatformAdminRevoked(user_id=self.id, email=self.email))

    def update_password(self, new_hashed_password: str) -> None:
        self.hashed_password = new_hashed_password
        self.updated_at = datetime.now(UTC)


@dataclass(eq=False, kw_only=True)
class UserTenant(BaseEntity):
    user_id: UUID
    tenant_id: UUID
    role: UserTenantRole
    joined_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        tenant_id: UUID,
        role: UserTenantRole = UserTenantRole.OWNER,
    ) -> UserTenant:
        link = cls(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            joined_at=datetime.now(UTC),
        )
        link._is_new = True
        link._emit(UserAddedToTenant(user_id=user_id, tenant_id=tenant_id, role=role))
        return link
