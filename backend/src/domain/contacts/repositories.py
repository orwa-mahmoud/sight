"""Contact repository port — persistence interface."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.contacts.entities import Contact


class ContactRepository(Protocol):
    """Port for contact persistence."""

    async def get_or_create_by_phone(
        self,
        tenant_id: UUID,
        phone: str,
        name: str | None = None,
    ) -> Contact:
        """Return existing contact or create a new one (INSERT ON CONFLICT).

        Uniqueness is scoped to (tenant_id, phone).
        """
        ...

    async def get_by_telegram_user_id(
        self,
        tenant_id: UUID,
        telegram_user_id: str,
    ) -> Contact | None:
        """Find a contact by their linked Telegram user ID within a tenant."""
        ...

    async def save(self, contact: Contact) -> None: ...

    async def get_by_id(self, contact_id: UUID) -> Contact | None: ...
