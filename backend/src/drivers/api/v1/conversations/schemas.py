"""Conversations API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ConversationSummary(BaseModel):
    id: UUID
    thread_id: str
    channel: str
    last_message_at: datetime | None
    created_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    hidden: bool
    tool_call_id: str | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    is_checkpoint: bool
    created_at: datetime
