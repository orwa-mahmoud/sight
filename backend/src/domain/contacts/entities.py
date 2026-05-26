"""Contact entity — external person who interacts with a tenant's front desk."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.contacts.events import ContactCreated
from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError


@dataclass(eq=False, kw_only=True)
class Contact(BaseEntity):
    """A channel user (WhatsApp sender, Telegram user) linked to a tenant.

    Simplified from PropertyBot's Client: no lead management, no blocking,
    no global-vs-tenant split.  Just identity + tenant scope.
    """

    tenant_id: UUID
    phone: str | None = None
    name: str | None = None
    email: str | None = None
    telegram_user_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        phone: str | None = None,
        name: str | None = None,
        email: str | None = None,
        telegram_user_id: str | None = None,
    ) -> Contact:
        if not phone and not telegram_user_id:
            raise InvalidOperationError("Contact must have at least a phone number or telegram_user_id")
        now = datetime.now(UTC)
        contact = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            phone=phone,
            name=name.strip() if name else None,
            email=email,
            telegram_user_id=telegram_user_id,
            created_at=now,
            updated_at=now,
        )
        contact._is_new = True
        contact._emit(
            ContactCreated(
                contact_id=contact.id,
                tenant_id=tenant_id,
                phone=phone,
            )
        )
        return contact

    def link_telegram(self, telegram_user_id: str) -> None:
        """Associate a Telegram user ID with this contact."""
        self.telegram_user_id = telegram_user_id
        self.updated_at = datetime.now(UTC)
