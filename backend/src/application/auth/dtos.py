"""DTOs returned by auth use cases — domain-shaped, framework-free."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class AuthResult:
    """Outcome of a successful register / login flow."""

    user_id: UUID
    tenant_id: UUID
    access_token: str
    token_type: str = "bearer"


@dataclass(frozen=True, kw_only=True)
class UserDTO:
    """Lightweight projection of a user for /me-style endpoints."""

    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_platform_admin: bool
    tenant_id: UUID
    tenant_slug: str
    tenant_name: str
    role: str
