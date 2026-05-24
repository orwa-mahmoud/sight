"""CloseQuestion — owner dismisses without reply."""

from __future__ import annotations

from src.application.questions.commands import CloseQuestion
from src.application.questions.dtos import QuestionDTO
from src.application.questions.use_cases._mapping import to_dto
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


class CloseQuestionUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: CloseQuestion) -> QuestionDTO:
        question = await self._uow.questions.get_by_id(cmd.question_id)
        if question is None:
            raise EntityNotFoundError("Question not found")
        if question.tenant_id != cmd.tenant_id:
            raise AuthorizationError("Question does not belong to this tenant")

        question.close()
        await self._uow.questions.save(question)
        return to_dto(question)
