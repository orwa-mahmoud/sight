"""PostgreSQL Question repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.conversations.value_objects import ConversationChannel
from src.domain.questions.entities import Question
from src.domain.questions.value_objects import QuestionStatus
from src.infrastructure.persistence.postgres.models.question import QuestionModel


class PostgresQuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, question: Question) -> None:
        if question.is_new:
            self._session.add(self._to_model(question))
            question.mark_persisted()
            return
        model = await self._session.get(QuestionModel, question.id)
        if model is None:
            self._session.add(self._to_model(question))
            return
        model.status = question.status.value
        model.owner_reply = question.owner_reply
        model.replied_by_user_id = question.replied_by_user_id
        model.replied_at = question.replied_at
        model.updated_at = question.updated_at

    async def get_by_id(self, question_id: UUID) -> Question | None:
        model = await self._session.get(QuestionModel, question_id)
        return self._to_entity(model) if model else None

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: QuestionStatus | None = None,
        limit: int = 100,
    ) -> list[Question]:
        stmt = select(QuestionModel).where(QuestionModel.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(QuestionModel.status == status.value)
        stmt = stmt.order_by(QuestionModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: QuestionStatus | None = None,
    ) -> int:
        stmt = select(func.count(QuestionModel.id)).where(QuestionModel.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(QuestionModel.status == status.value)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_since(self, tenant_id: UUID, since: datetime) -> int:
        result = await self._session.execute(
            select(func.count(QuestionModel.id)).where(
                QuestionModel.tenant_id == tenant_id,
                QuestionModel.created_at >= since,
            )
        )
        return int(result.scalar_one())

    @staticmethod
    def _to_model(q: Question) -> QuestionModel:
        return QuestionModel(
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

    @staticmethod
    def _to_entity(m: QuestionModel) -> Question:
        return Question(
            id=m.id,
            tenant_id=m.tenant_id,
            conversation_id=m.conversation_id,
            channel=ConversationChannel(m.channel),
            contact_id=m.contact_id,
            question_text=m.question_text,
            ai_answer_attempt=m.ai_answer_attempt,
            status=QuestionStatus(m.status),
            owner_reply=m.owner_reply,
            replied_by_user_id=m.replied_by_user_id,
            replied_at=m.replied_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
