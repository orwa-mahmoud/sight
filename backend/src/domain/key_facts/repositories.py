"""KeyFact repository port."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.key_facts.entities import KeyFact


class KeyFactRepository(Protocol):
    async def save(self, fact: KeyFact) -> None: ...

    async def get(self, tenant_id: UUID, participant_identifier: str, key: str) -> KeyFact | None: ...

    async def list_for_participant(self, tenant_id: UUID, participant_identifier: str) -> list[KeyFact]: ...

    async def delete(self, fact_id: UUID) -> None: ...
