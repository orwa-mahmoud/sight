"""KeyFact entity — one fact per (tenant, contact, key)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError


@dataclass(eq=False, kw_only=True)
class KeyFact(BaseEntity):
    tenant_id: UUID
    contact_id: UUID  # FK → contacts.id
    key: str  # e.g. "name", "preferred_language", "budget"
    value: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        contact_id: UUID,
        key: str,
        value: str,
    ) -> KeyFact:
        clean_key = key.strip().lower()
        clean_value = value.strip()
        if not clean_key:
            raise InvalidOperationError("Key fact key cannot be empty")
        if not clean_value:
            raise InvalidOperationError("Key fact value cannot be empty")
        now = datetime.now(UTC)
        fact = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            contact_id=contact_id,
            key=clean_key,
            value=clean_value,
            created_at=now,
            updated_at=now,
        )
        fact._is_new = True
        return fact

    def update_value(self, new_value: str) -> None:
        clean = new_value.strip()
        if not clean:
            raise InvalidOperationError("Key fact value cannot be empty")
        self.value = clean
        self.updated_at = datetime.now(UTC)
