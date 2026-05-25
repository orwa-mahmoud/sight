"""remove_key_fact tool — delete a previously saved fact."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.ai.types import ToolDef
from src.infrastructure.persistence.postgres.repositories.key_fact_repo import PostgresKeyFactRepository

REMOVE_KEY_FACT_DEF = ToolDef(
    name="remove_key_fact",
    description="Remove a previously saved fact about the current asker.",
    parameters_schema={
        "type": "object",
        "properties": {"key": {"type": "string", "description": "The fact key to remove"}},
        "required": ["key"],
    },
)


async def run_remove_key_fact(
    *,
    arguments: dict[str, Any],
    tenant_id: UUID,
    contact_id: UUID,
    session: Any,
) -> dict[str, str]:
    key = arguments.get("key", "").strip().lower()
    if not key:
        return {"status": "skipped", "reason": "empty key"}
    repo = PostgresKeyFactRepository(session)
    existing = await repo.get(tenant_id, contact_id, key)
    if not existing:
        return {"status": "not_found", "key": key}
    await repo.delete(existing.id)
    return {"status": "removed", "key": key}
