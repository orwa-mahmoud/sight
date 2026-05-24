"""Question DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class QuestionDTO:
    id: UUID
    tenant_id: UUID
    conversation_id: UUID | None
    channel: str
    asker_name: str | None
    asker_contact: str | None
    question_text: str
    ai_answer_attempt: str | None
    status: str
    owner_reply: str | None
    replied_by_user_id: UUID | None
    replied_at: datetime | None
    created_at: datetime
    updated_at: datetime
