"""Key facts context loader — injects known facts into the system prompt.

Before the agent runs, we load all key facts for the current contact
and append them to the system prompt so the AI knows who it's talking
to without having to search the DB every turn.
"""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork

# Facts are injected into the system prompt every turn; cap the count so a
# long-lived contact's accumulated facts can't bloat the prompt unboundedly.
_MAX_FACTS = 50


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
    if len(facts) > _MAX_FACTS:
        # Keep the most recently updated facts — they're the most relevant.
        facts = sorted(facts, key=lambda f: f.updated_at, reverse=True)[:_MAX_FACTS]
    lines = ["Known facts about this asker:"]
    for f in facts:
        lines.append(f"- {f.key}: {f.value}")
    return "\n".join(lines)
