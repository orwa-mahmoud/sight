"""KeyFact repository port."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.key_facts.entities import KeyFact


class KeyFactRepository(Protocol):
    async def save(self, fact: KeyFact) -> None: ...

    async def get(self, tenant_id: UUID, contact_id: UUID, key: str) -> KeyFact | None: ...

    async def list_for_contact(self, tenant_id: UUID, contact_id: UUID) -> list[KeyFact]: ...

    async def list_for_tenant(self, tenant_id: UUID, *, limit: int = 500) -> list[KeyFact]: ...

    async def delete(self, fact_id: UUID) -> None: ...
