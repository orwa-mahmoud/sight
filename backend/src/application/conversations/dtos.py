"""Conversation DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class ThreadMessageDTO:
    id: UUID
    role: str
    content: str
    hidden: bool
    tool_call_id: str | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    is_compressed: bool
    compressed_summary: str | None
    is_checkpoint: bool
    token_count: int
    request_id: str | None
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class SaveMessageResult:
    message_id: UUID
    conversation_id: UUID
    # True when an inbound message was skipped because its provider_message_id
    # was already saved for this conversation (durable de-duplication).
    is_duplicate: bool = False
