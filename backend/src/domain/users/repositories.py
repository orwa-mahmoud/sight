"""User + UserTenant repository ports."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.users.entities import User, UserTenant


class UserRepository(Protocol):
    async def save(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...


class UserTenantRepository(Protocol):
    async def save(self, link: UserTenant) -> None: ...

    async def list_for_user(self, user_id: UUID) -> list[UserTenant]: ...

    async def get(self, user_id: UUID, tenant_id: UUID) -> UserTenant | None: ...
