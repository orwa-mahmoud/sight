"""Direct chat API — test endpoint for the agent without channel webhooks.

Authenticated owners can send a message as if they were an asker,
useful for testing the agent loop, RAG retrieval, and escalation
without setting up WhatsApp or Telegram.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    escalated: bool
    request_id: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, current_user: CurrentUser, uow: UnitOfWorkDep) -> ChatResponse:
    """Send a test message through the full agent pipeline."""
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    tenant_id = links[0].tenant_id

    result = await chat_with_agent(
        ChatInput(
            message=req.message,
            tenant_id=tenant_id,
            channel=ConversationChannel.API,
            sender_identifier=current_user.email,
            sender_name=current_user.full_name,
        ),
        uow=uow,
    )

    return ChatResponse(
        response=result.response,
        thread_id=result.thread_id,
        escalated=result.escalated,
        request_id=result.request_id,
    )
