"""Conversations routes — list threads + get messages."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from src.domain.shared.exceptions import AuthenticationError, AuthorizationError, EntityNotFoundError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.drivers.api.v1.conversations.schemas import ConversationSummary, MessageResponse
from src.infrastructure.persistence.postgres.models.conversation import ConversationModel

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _resolve_tenant_id(current_user: CurrentUser, uow: UnitOfWorkDep) -> UUID:
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    return links[0].tenant_id


@router.get("")
async def list_conversations(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> list[ConversationSummary]:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.tenant_id == tenant_id)
        .order_by(ConversationModel.last_message_at.desc().nullslast())
        .limit(100)
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


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> list[MessageResponse]:
    tenant_id = await _resolve_tenant_id(current_user, uow)
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
