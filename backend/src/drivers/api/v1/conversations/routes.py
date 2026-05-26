"""Conversations routes — list threads + get messages + daily summary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep, resolve_tenant_id
from src.drivers.api.v1.conversations.schemas import ConversationSummary, DailySummaryResponse, MessageResponse
from src.infrastructure.persistence.postgres.models.conversation import ConversationModel
from src.infrastructure.persistence.postgres.models.message import MessageModel
from src.infrastructure.persistence.postgres.models.question import QuestionModel

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversationSummary]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.tenant_id == tenant_id)
        .order_by(ConversationModel.last_message_at.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    result = await uow._session.execute(stmt)
    return [
        ConversationSummary(
            id=c.id,
            thread_id=c.thread_id,
            channel=c.channel,
            last_message_at=c.last_message_at,
            created_at=c.created_at,
        )
        for c in result.scalars().all()
    ]


@router.get("/daily-summary")
async def daily_summary(current_user: CurrentUser, uow: UnitOfWorkDep) -> DailySummaryResponse:
    """What happened today — message count, conversation count, question count."""
    tenant_id = await resolve_tenant_id(current_user, uow)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    session = uow._session

    msg_count = (
        await session.execute(
            select(func.count(MessageModel.id)).where(
                MessageModel.tenant_id == tenant_id,
                MessageModel.created_at >= today,
                MessageModel.hidden.is_(False),
            )
        )
    ).scalar_one()

    conv_count = (
        await session.execute(
            select(func.count(ConversationModel.id)).where(
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.last_message_at >= today,
            )
        )
    ).scalar_one()

    question_count = (
        await session.execute(
            select(func.count(QuestionModel.id)).where(
                QuestionModel.tenant_id == tenant_id,
                QuestionModel.created_at >= today,
            )
        )
    ).scalar_one()

    return DailySummaryResponse(
        date=today.date().isoformat(),
        total_messages=int(msg_count),
        active_conversations=int(conv_count),
        questions_escalated=int(question_count),
    )


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> list[MessageResponse]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    conv = await uow.conversations.get_by_id(conversation_id)
    if conv is None:
        raise EntityNotFoundError("Conversation not found")
    if conv.tenant_id != tenant_id:
        raise AuthorizationError("Conversation does not belong to this tenant")

    messages = await uow.messages.list_for_conversation(conversation_id, include_hidden=False)
    return [
        MessageResponse(
            id=m.id,
            role=m.role.value,
            content=m.content,
            hidden=m.hidden,
            tool_call_id=m.tool_call_id,
            tool_args=m.tool_args,
            tool_result=m.tool_result,
            is_checkpoint=m.is_checkpoint,
            created_at=m.created_at,
        )
        for m in messages
    ]
