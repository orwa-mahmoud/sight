"""User domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent
from src.domain.users.value_objects import UserTenantRole


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class UserAddedToTenant(DomainEvent):
    user_id: UUID
    tenant_id: UUID
    role: UserTenantRole
