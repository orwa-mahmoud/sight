"""save_key_fact tool — agent-driven persistent memory.

Called by the agent when it learns something about the asker that should
be remembered across conversations (e.g. name, preferred language, time
zone). If a fact with the same key already exists, it's updated.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.ai.types import ToolDef
from src.domain.key_facts.entities import KeyFact
from src.infrastructure.persistence.postgres.repositories.key_fact_repo import PostgresKeyFactRepository

SAVE_KEY_FACT_DEF = ToolDef(
    name="save_key_fact",
    description=(
        "Save a fact about the current asker for future reference. "
        "Use this when you learn the asker's name, language preference, "
        "or any other persistent detail. If the fact already exists, it's updated."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "The fact key (e.g. 'name', 'language', 'timezone')"},
            "value": {"type": "string", "description": "The fact value"},
        },
        "required": ["key", "value"],
    },
)


async def run_save_key_fact(
    *,
    arguments: dict[str, Any],
    tenant_id: UUID,
    participant_identifier: str,
    session: Any,
) -> dict[str, str]:
    key = arguments.get("key", "").strip().lower()
    value = arguments.get("value", "").strip()
    if not key or not value:
        return {"status": "skipped", "reason": "empty key or value"}

    repo = PostgresKeyFactRepository(session)
    existing = await repo.get(tenant_id, participant_identifier, key)
    if existing:
        existing.update_value(value)
        await repo.save(existing)
        return {"status": "updated", "key": key}

    fact = KeyFact.create(
        tenant_id=tenant_id,
        participant_identifier=participant_identifier,
        key=key,
        value=value,
    )
    await repo.save(fact)
    return {"status": "saved", "key": key}
