"""Question commands."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.conversations.value_objects import ConversationChannel


@dataclass(frozen=True, kw_only=True)
class SubmitQuestion:
    tenant_id: UUID
    channel: ConversationChannel
    question_text: str
    conversation_id: UUID | None = None
    contact_id: UUID | None = None
    ai_answer_attempt: str | None = None


@dataclass(frozen=True, kw_only=True)
class ReplyToQuestion:
    tenant_id: UUID
    question_id: UUID
    replied_by_user_id: UUID
    reply: str


@dataclass(frozen=True, kw_only=True)
class CloseQuestion:
    tenant_id: UUID
    question_id: UUID
