"""Key facts context loader — injects known facts into the system prompt.

Before the agent runs, we load all key facts for the current contact
and append them to the system prompt so the AI knows who it's talking
to without having to search the DB every turn.
"""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork


async def load_key_facts_context(
    *,
    tenant_id: UUID,
    contact_id: UUID,
    uow: UnitOfWork,
) -> str:
    """Return a formatted string of known facts for this contact, or empty."""
    facts = await uow.key_facts.list_for_contact(tenant_id, contact_id)
    if not facts:
        return ""
    lines = ["Known facts about this asker:"]
    for f in facts:
        lines.append(f"- {f.key}: {f.value}")
    return "\n".join(lines)
