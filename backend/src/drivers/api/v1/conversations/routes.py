"""Conversations routes — list threads + get messages + daily summary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep, resolve_tenant_id
from src.drivers.api.v1.conversations.schemas import ConversationSummary, DailySummaryResponse, MessageResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
async def list_conversations(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ConversationSummary]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    convs = await uow.conversations.list_for_tenant(tenant_id, limit=limit, offset=offset)
    return [
        ConversationSummary(
            id=c.id,
            thread_id=c.thread_id,
            channel=c.channel.value,
            last_message_at=c.last_message_at,
            created_at=c.created_at,
        )
        for c in convs
    ]


@router.get("/daily-summary")
async def daily_summary(current_user: CurrentUser, uow: UnitOfWorkDep) -> DailySummaryResponse:
    """What happened today — message count, conversation count, question count."""
    tenant_id = await resolve_tenant_id(current_user, uow)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    msg_count = await uow.messages.count_visible_since(tenant_id, today)
    conv_count = await uow.conversations.count_active_since(tenant_id, today)
    question_count = await uow.questions.count_since(tenant_id, today)

    return DailySummaryResponse(
        date=today.date().isoformat(),
        total_messages=msg_count,
        active_conversations=conv_count,
        questions_escalated=question_count,
    )


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[MessageResponse]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    conv = await uow.conversations.get_by_id(conversation_id)
    if conv is None:
        raise EntityNotFoundError("Conversation not found")
    if conv.tenant_id != tenant_id:
        raise AuthorizationError("Conversation does not belong to this tenant")

    # Long-lived threads accumulate unbounded turns; cap the dashboard read to the
    # most recent `limit` (chronological) so the payload + response time stay bounded.
    messages = await uow.messages.list_for_conversation(conversation_id, include_hidden=False, limit=limit)
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
