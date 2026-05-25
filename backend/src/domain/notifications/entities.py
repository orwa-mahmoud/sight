"""Notification failure entity -- records failed delivery attempts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class NotificationFailure:
    """A failed notification delivery attempt."""

    id: UUID
    tenant_id: UUID
    recipient_id: UUID
    recipient_type: str  # "contact", "user", "owner"
    reason: str
    context_data: dict[str, Any]
    created_at: datetime
    entity_type: str = ""  # optional: the entity type that triggered the notification
    entity_id: str = ""  # optional: the entity ID

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        recipient_id: UUID,
        recipient_type: str,
        reason: str,
        entity_type: str = "",
        entity_id: str = "",
        context_data: dict[str, Any] | None = None,
    ) -> NotificationFailure:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            reason=reason,
            context_data=context_data or {},
            created_at=datetime.now(UTC),
            entity_type=entity_type,
            entity_id=entity_id,
        )
