"""DTOs returned by admin use cases — domain-shaped, framework-free."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class AdminTenantDTO:
    """A tenant row for the platform-admin tenants table."""

    id: UUID
    name: str
    slug: str
    status: str
    owner_email: str | None
    user_count: int
    document_count: int


@dataclass(frozen=True, kw_only=True)
class AdminUserDTO:
    """A user row for the platform-admin users table."""

    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    tenant_id: UUID | None
    tenant_name: str | None
    role: str | None
