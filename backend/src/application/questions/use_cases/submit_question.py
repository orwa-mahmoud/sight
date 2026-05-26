"""SubmitQuestion — create an escalation row from an agent tool or webhook."""

from __future__ import annotations

from src.application.questions.commands import SubmitQuestion
from src.application.questions.dtos import QuestionDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.questions.entities import Question

from ._mapping import to_dto


class SubmitQuestionUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: SubmitQuestion) -> QuestionDTO:
        question = Question.submit(
            tenant_id=cmd.tenant_id,
            channel=cmd.channel,
            question_text=cmd.question_text,
            conversation_id=cmd.conversation_id,
            contact_id=cmd.contact_id,
            ai_answer_attempt=cmd.ai_answer_attempt,
        )
        await self._uow.questions.save(question)
        self._uow.track(question)
        return to_dto(question)
