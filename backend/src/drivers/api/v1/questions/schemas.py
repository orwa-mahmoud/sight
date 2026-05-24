"""Questions API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.conversations.value_objects import ConversationChannel
from src.domain.questions.value_objects import QuestionStatus


class SubmitQuestionRequest(BaseModel):
    channel: ConversationChannel
    question_text: str = Field(min_length=1, max_length=10_000)
    asker_name: str | None = Field(default=None, max_length=255)
    asker_contact: str | None = Field(default=None, max_length=255)
    ai_answer_attempt: str | None = Field(default=None, max_length=10_000)
    conversation_id: UUID | None = None


class ReplyRequest(BaseModel):
    reply: str = Field(min_length=1, max_length=10_000)


class QuestionResponse(BaseModel):
    id: UUID
    conversation_id: UUID | None
    channel: str
    asker_name: str | None
    asker_contact: str | None
    question_text: str
    ai_answer_attempt: str | None
    status: QuestionStatus
    owner_reply: str | None
    replied_by_user_id: UUID | None
    replied_at: datetime | None
    created_at: datetime
    updated_at: datetime
