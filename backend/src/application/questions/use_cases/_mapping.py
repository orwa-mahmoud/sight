"""Shared mapping helpers for question use cases."""

from __future__ import annotations

from src.application.questions.dtos import QuestionDTO
from src.domain.questions.entities import Question


def to_dto(q: Question) -> QuestionDTO:
    return QuestionDTO(
        id=q.id,
        tenant_id=q.tenant_id,
        conversation_id=q.conversation_id,
        channel=q.channel.value,
        contact_id=q.contact_id,
        question_text=q.question_text,
        ai_answer_attempt=q.ai_answer_attempt,
        status=q.status.value,
        owner_reply=q.owner_reply,
        replied_by_user_id=q.replied_by_user_id,
        replied_at=q.replied_at,
        created_at=q.created_at,
        updated_at=q.updated_at,
    )
