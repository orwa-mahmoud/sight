"""Contact domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ContactCreated(DomainEvent):
    """Emitted when a new contact is created."""

    contact_id: UUID
    tenant_id: UUID
    phone: str | None
