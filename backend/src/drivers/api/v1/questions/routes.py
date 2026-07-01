"""Questions routes — submit, list, get, reply, close.

Submit is intentionally authenticated in v1 so it's callable from the
agent loop's tool (which runs as the tenant). In the channels phase,
webhook handlers will submit via a dedicated internal entry that
bypasses auth (signed by the channel's secret instead).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Query, status

from src.application.questions.commands import CloseQuestion, ReplyToQuestion, SubmitQuestion
from src.application.questions.dtos import QuestionDTO
from src.application.questions.queries import GetQuestion, ListQuestions
from src.application.questions.use_cases.close_question import CloseQuestionUseCase
from src.application.questions.use_cases.list_questions import (
    GetQuestionUseCase,
    ListQuestionsUseCase,
)
from src.application.questions.use_cases.reply_to_question import ReplyToQuestionUseCase
from src.application.questions.use_cases.submit_question import SubmitQuestionUseCase
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.questions.value_objects import QuestionStatus
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep, resolve_tenant_id
from src.drivers.api.v1.questions.schemas import (
    QuestionResponse,
    ReplyRequest,
    SubmitQuestionRequest,
)
from src.infrastructure.channels.cache import get_telegram_adapter, get_whatsapp_adapter

router = APIRouter(prefix="/questions", tags=["questions"])


logger = structlog.get_logger()


async def _deliver_reply(dto: object, uow: UnitOfWorkDep) -> None:
    """Best-effort: send the owner's reply back to the asker via the original channel."""
    assert isinstance(dto, QuestionDTO)
    if not dto.owner_reply or not dto.contact_id or not dto.channel:
        return

    try:
        contact = await uow.contacts.get_by_id(dto.contact_id)
        # Defense in depth: never deliver a reply to a contact owned by another
        # tenant, even if a legacy row references one.
        if not contact or contact.tenant_id != dto.tenant_id or not contact.phone:
            return
        config = await uow.tenant_configs.get_by_tenant_id(dto.tenant_id)
        if not config:
            return

        channel = ConversationChannel(dto.channel)
        if channel == ConversationChannel.WHATSAPP and config.whatsapp_access_token and contact.phone:
            wa = await get_whatsapp_adapter(
                str(dto.tenant_id),
                phone_number_id=config.whatsapp_phone_number_id or "",
                access_token=config.whatsapp_access_token or "",
            )
            await wa.send_text(contact.phone, dto.owner_reply)
        elif channel == ConversationChannel.TELEGRAM and config.telegram_bot_token:
            tg_recipient = getattr(contact, "telegram_user_id", None) or contact.phone
            if tg_recipient:
                tg = await get_telegram_adapter(str(dto.tenant_id), tenant_config=config)
                await tg.send_text(tg_recipient, dto.owner_reply)
    except Exception:
        logger.warning("question.reply_delivery.failed", question_id=str(dto.id), exc_info=True)


def _to_response(dto: object) -> QuestionResponse:
    assert isinstance(dto, QuestionDTO)
    return QuestionResponse(
        id=dto.id,
        conversation_id=dto.conversation_id,
        channel=dto.channel,
        contact_id=dto.contact_id,
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
    tenant_id = await resolve_tenant_id(current_user, uow)
    dto = await SubmitQuestionUseCase(uow=uow).execute(
        SubmitQuestion(
            tenant_id=tenant_id,
            channel=req.channel,
            question_text=req.question_text,
            conversation_id=req.conversation_id,
            contact_id=req.contact_id,
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
    tenant_id = await resolve_tenant_id(current_user, uow)
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
    tenant_id = await resolve_tenant_id(current_user, uow)
    dto = await GetQuestionUseCase(uow=uow).execute(GetQuestion(tenant_id=tenant_id, question_id=question_id))
    return _to_response(dto)


@router.post("/{question_id}/reply")
async def reply(
    question_id: UUID,
    req: ReplyRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> QuestionResponse:
    tenant_id = await resolve_tenant_id(current_user, uow)
    dto = await ReplyToQuestionUseCase(uow=uow).execute(
        ReplyToQuestion(
            tenant_id=tenant_id,
            question_id=question_id,
            replied_by_user_id=current_user.id,
            reply=req.reply,
        )
    )
    await _deliver_reply(dto, uow)
    return _to_response(dto)


@router.post("/{question_id}/close")
async def close_question(
    question_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> QuestionResponse:
    tenant_id = await resolve_tenant_id(current_user, uow)
    dto = await CloseQuestionUseCase(uow=uow).execute(CloseQuestion(tenant_id=tenant_id, question_id=question_id))
    return _to_response(dto)
