"""KeyFact entity — one fact per (tenant, participant, key)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.shared.entities import BaseEntity


@dataclass(eq=False, kw_only=True)
class KeyFact(BaseEntity):
    tenant_id: UUID
    participant_identifier: str  # phone, email, telegram_user_id
    key: str  # e.g. "name", "preferred_language", "budget"
    value: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        participant_identifier: str,
        key: str,
        value: str,
    ) -> KeyFact:
        now = datetime.now(UTC)
        fact = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            participant_identifier=participant_identifier.strip(),
            key=key.strip().lower(),
            value=value.strip(),
            created_at=now,
            updated_at=now,
        )
        fact._is_new = True
        return fact

    def update_value(self, new_value: str) -> None:
        self.value = new_value.strip()
        self.updated_at = datetime.now(UTC)
