"""Question aggregate — one escalated question, with state machine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.conversations.value_objects import ConversationChannel
from src.domain.questions.events import QuestionClosed, QuestionResolved, QuestionSubmitted
from src.domain.questions.value_objects import QuestionStatus
from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError


@dataclass(eq=False, kw_only=True)
class Question(BaseEntity):
    tenant_id: UUID
    conversation_id: UUID | None  # set when escalation arose from a chat
    channel: ConversationChannel
    asker_name: str | None
    asker_contact: str | None  # phone / email / telegram handle — channel-specific
    question_text: str
    ai_answer_attempt: str | None  # what the AI tried before giving up
    status: QuestionStatus
    owner_reply: str | None = None
    replied_by_user_id: UUID | None = None
    replied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def submit(
        cls,
        *,
        tenant_id: UUID,
        channel: ConversationChannel,
        question_text: str,
        conversation_id: UUID | None = None,
        asker_name: str | None = None,
        asker_contact: str | None = None,
        ai_answer_attempt: str | None = None,
    ) -> Question:
        cleaned = question_text.strip()
        if not cleaned:
            raise InvalidOperationError("Question text cannot be empty")

        now = datetime.now(UTC)
        q = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            channel=channel,
            asker_name=asker_name.strip() if asker_name else None,
            asker_contact=asker_contact.strip() if asker_contact else None,
            question_text=cleaned,
            ai_answer_attempt=ai_answer_attempt,
            status=QuestionStatus.SUBMITTED,
            created_at=now,
            updated_at=now,
        )
        q._is_new = True
        q._emit(
            QuestionSubmitted(
                question_id=q.id,
                tenant_id=tenant_id,
                channel=channel.value,
                asker_contact=q.asker_contact,
            )
        )
        return q

    def resolve(self, *, reply: str, replied_by_user_id: UUID) -> None:
        if self.status != QuestionStatus.SUBMITTED:
            raise InvalidOperationError(f"Cannot reply to a question in status {self.status}")
        clean_reply = reply.strip()
        if not clean_reply:
            raise InvalidOperationError("Reply cannot be empty")
        now = datetime.now(UTC)
        self.owner_reply = clean_reply
        self.replied_by_user_id = replied_by_user_id
        self.replied_at = now
        self.status = QuestionStatus.RESOLVED
        self.updated_at = now
        self._emit(
            QuestionResolved(
                question_id=self.id,
                tenant_id=self.tenant_id,
                replied_by_user_id=replied_by_user_id,
            )
        )

    def close(self) -> None:
        if self.status == QuestionStatus.CLOSED:
            raise InvalidOperationError("Question is already closed")
        self.status = QuestionStatus.CLOSED
        self.updated_at = datetime.now(UTC)
        self._emit(QuestionClosed(question_id=self.id, tenant_id=self.tenant_id))
