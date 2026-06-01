"""ReplyToQuestion — owner answers, status moves to RESOLVED.

A `QuestionResolved` event fires (handled in bootstrap for metrics/logging).
The reply is delivered back to the asker over the original channel by the
route handler's best-effort `_deliver_reply` after this use case returns —
delivery is an adapter concern and stays out of the application layer.
"""

from __future__ import annotations

from src.application.questions.commands import ReplyToQuestion
from src.application.questions.dtos import QuestionDTO
from src.application.questions.use_cases._mapping import to_dto
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


class ReplyToQuestionUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: ReplyToQuestion) -> QuestionDTO:
        question = await self._uow.questions.get_by_id(cmd.question_id)
        if question is None:
            raise EntityNotFoundError("Question not found", code="question.not_found")
        if question.tenant_id != cmd.tenant_id:
            raise AuthorizationError("Question does not belong to this tenant", code="question.forbidden")

        question.resolve(reply=cmd.reply, replied_by_user_id=cmd.replied_by_user_id)
        await self._uow.questions.save(question)
        self._uow.track(question)
        return to_dto(question)
