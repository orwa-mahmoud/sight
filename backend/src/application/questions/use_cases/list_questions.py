"""ListQuestions + GetQuestion — owner inbox queries."""

from __future__ import annotations

from src.application.questions.dtos import QuestionDTO
from src.application.questions.queries import GetQuestion, ListQuestions
from src.application.questions.use_cases._mapping import to_dto
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


class ListQuestionsUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListQuestions) -> list[QuestionDTO]:
        questions = await self._uow.questions.list_for_tenant(
            query.tenant_id,
            status=query.status,
            limit=query.limit,
        )
        return [to_dto(q) for q in questions]


class GetQuestionUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetQuestion) -> QuestionDTO:
        question = await self._uow.questions.get_by_id(query.question_id)
        if question is None:
            raise EntityNotFoundError("Question not found", code="question.not_found")
        if question.tenant_id != query.tenant_id:
            raise AuthorizationError("Question does not belong to this tenant", code="question.forbidden")
        return to_dto(question)
