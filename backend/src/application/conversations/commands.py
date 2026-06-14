"""Conversation commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.domain.conversations.value_objects import ConversationChannel, ConversationRole


@dataclass(frozen=True, kw_only=True)
class SaveThreadMessage:
    tenant_id: UUID
    thread_id: str
    channel: ConversationChannel
    role: ConversationRole
    content: str
    hidden: bool = False
    participant_id: UUID | None = None
    tool_call_id: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    is_checkpoint: bool = False
    token_count: int = 0
    request_id: str | None = None
    # Provider message id (WhatsApp wamid / Telegram message_id). When set, the
    # save is de-duplicated against (conversation, provider_message_id).
    provider_message_id: str | None = None
