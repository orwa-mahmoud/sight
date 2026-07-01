"""SubmitQuestion — create an escalation row from an agent tool or webhook."""

from __future__ import annotations

from src.application.questions.commands import SubmitQuestion
from src.application.questions.dtos import QuestionDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.questions.entities import Question
from src.domain.shared.exceptions import AuthorizationError

from ._mapping import to_dto


class SubmitQuestionUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: SubmitQuestion) -> QuestionDTO:
        # tenant_id is resolved from auth upstream, but the referenced contact and
        # conversation are client-supplied — reject any that belong to another tenant,
        # or the reply could be persisted against (and delivered to) a foreign contact.
        if cmd.contact_id is not None:
            contact = await self._uow.contacts.get_by_id(cmd.contact_id)
            if contact is None or contact.tenant_id != cmd.tenant_id:
                raise AuthorizationError("Contact does not belong to this tenant", code="question.foreign_contact")
        if cmd.conversation_id is not None:
            conversation = await self._uow.conversations.get_by_id(cmd.conversation_id)
            if conversation is None or conversation.tenant_id != cmd.tenant_id:
                raise AuthorizationError(
                    "Conversation does not belong to this tenant", code="question.foreign_conversation"
                )

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
