"""DTOs returned by invitation use cases — domain-shaped, framework-free."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class InvitationDTO:
    id: UUID
    tenant_id: UUID
    email: str
    role: str
    status: str
    token: str
    expires_at: datetime
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class InvitationPreviewDTO:
    """Public-facing view of an invite, by token (no token echoed back)."""

    tenant_name: str
    email: str
    role: str
    status: str
    valid: bool
