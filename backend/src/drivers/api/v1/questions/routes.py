"""Questions routes — submit, list, get, reply, close.

Submit is intentionally authenticated in v1 so it's callable from the
agent loop's tool (which runs as the tenant). In the channels phase,
webhook handlers will submit via a dedicated internal entry that
bypasses auth (signed by the channel's secret instead).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from src.application.questions.commands import CloseQuestion, ReplyToQuestion, SubmitQuestion
from src.application.questions.queries import GetQuestion, ListQuestions
from src.application.questions.use_cases.close_question import CloseQuestionUseCase
from src.application.questions.use_cases.list_questions import (
    GetQuestionUseCase,
    ListQuestionsUseCase,
)
from src.application.questions.use_cases.reply_to_question import ReplyToQuestionUseCase
from src.application.questions.use_cases.submit_question import SubmitQuestionUseCase
from src.domain.questions.value_objects import QuestionStatus
from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.drivers.api.v1.questions.schemas import (
    QuestionResponse,
    ReplyRequest,
    SubmitQuestionRequest,
)

router = APIRouter(prefix="/questions", tags=["questions"])


async def _resolve_tenant_id(current_user: CurrentUser, uow: UnitOfWorkDep) -> UUID:
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    return links[0].tenant_id


def _to_response(dto: object) -> QuestionResponse:
    from src.application.questions.dtos import QuestionDTO  # noqa: PLC0415

    assert isinstance(dto, QuestionDTO)
    return QuestionResponse(
        id=dto.id,
        conversation_id=dto.conversation_id,
        channel=dto.channel,
        asker_name=dto.asker_name,
        asker_contact=dto.asker_contact,
        question_text=dto.question_text,
        ai_answer_attempt=dto.ai_answer_attempt,
        status=QuestionStatus(dto.status),
        owner_reply=dto.owner_reply,
        replied_by_user_id=dto.replied_by_user_id,
        replied_at=dto.replied_at,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit(
    req: SubmitQuestionRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> QuestionResponse:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    dto = await SubmitQuestionUseCase(uow=uow).execute(
        SubmitQuestion(
            tenant_id=tenant_id,
            channel=req.channel,
            question_text=req.question_text,
            conversation_id=req.conversation_id,
            asker_name=req.asker_name,
            asker_contact=req.asker_contact,
            ai_answer_attempt=req.ai_answer_attempt,
        )
    )
    return _to_response(dto)


@router.get("")
async def list_questions(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    status_filter: Annotated[QuestionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[QuestionResponse]:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    dtos = await ListQuestionsUseCase(uow=uow).execute(
        ListQuestions(tenant_id=tenant_id, status=status_filter, limit=limit)
    )
    return [_to_response(d) for d in dtos]


@router.get("/{question_id}")
async def get_question(
    question_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> QuestionResponse:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    dto = await GetQuestionUseCase(uow=uow).execute(GetQuestion(tenant_id=tenant_id, question_id=question_id))
    return _to_response(dto)


@router.post("/{question_id}/reply")
async def reply(
    question_id: UUID,
    req: ReplyRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> QuestionResponse:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    dto = await ReplyToQuestionUseCase(uow=uow).execute(
        ReplyToQuestion(
            tenant_id=tenant_id,
            question_id=question_id,
            replied_by_user_id=current_user.id,
            reply=req.reply,
        )
    )
    return _to_response(dto)


@router.post("/{question_id}/close")
async def close_question(
    question_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> QuestionResponse:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    dto = await CloseQuestionUseCase(uow=uow).execute(CloseQuestion(tenant_id=tenant_id, question_id=question_id))
    return _to_response(dto)
