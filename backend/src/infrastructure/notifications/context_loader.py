"""Notification context loaders -- loads entity data for notification generation.

Ported from PropertyBot with property/viewing-specific loaders removed.
Provides the RecipientInfo dataclass and a registry pattern for future
entity-specific context loaders.

Frontdesk entities that may need notifications: questions (escalated
question replies sent back to the asker).
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


# -- Typed notification context ------------------------------------------------


@dataclass(frozen=True)
class RecipientInfo:
    """Minimal info about a notification recipient (contact or user)."""

    id: str
    name: str | None
    phone: str | None
    telegram_user_id: str | None


# -- Context loader registry --------------------------------------------------
# Maps entity_type to its context loader function. New loaders register here
# when entity-specific notification context is needed (e.g. question replies).
CONTEXT_LOADERS: dict[str, object] = {}
