"""Tests for checkpoint summarization with mocked LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.ai.context.checkpoint import _build_summarizer_input, maybe_create_checkpoint
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.entities import Conversation, Message
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.llm.value_objects import LLMCallResult, TokenUsage
from src.infrastructure.persistence.postgres.database import async_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_not_triggered_below_threshold(client: None) -> None:
    """If tokens since last checkpoint < 3000, no checkpoint is created."""
    tenant_id = uuid4()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.tenants.entities import Tenant

        t = Tenant.create(name="CP", slug=f"cp-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        tenant_id = t.id

        conv = Conversation.start(
            tenant_id=tenant_id, thread_id=f"cp-{uuid4().hex[:8]}", channel=ConversationChannel.WEB
        )
        await uow.conversations.save(conv)
        await uow.flush()

        msg = Message.create(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role=ConversationRole.USER,
            content="short msg",
            token_count=10,
        )
        await uow.messages.save(msg)
        await uow.commit()

        mock_llm = AsyncMock()
        await maybe_create_checkpoint(
            thread_id=conv.thread_id,
            tenant_id=tenant_id,
            channel=ConversationChannel.WEB,
            llm=mock_llm,
            uow=uow,
        )
        # LLM should NOT have been called
        mock_llm.chat_with_tools.assert_not_called()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_triggered_above_threshold(client: None) -> None:
    """When tokens exceed 3000, a checkpoint message is created."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        from src.domain.tenants.entities import Tenant

        t = Tenant.create(name="CP2", slug=f"cp2-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()

        thread_id = f"cp2-{uuid4().hex[:8]}"
        conv = Conversation.start(tenant_id=t.id, thread_id=thread_id, channel=ConversationChannel.WEB)
        await uow.conversations.save(conv)
        await uow.flush()

        # Add messages totaling >3000 tokens
        for i in range(10):
            msg = Message.create(
                conversation_id=conv.id,
                tenant_id=t.id,
                role=ConversationRole.USER,
                content=f"message {i}" * 50,
                token_count=400,
            )
            await uow.messages.save(msg)
        await uow.commit()

        mock_llm = AsyncMock()
        mock_llm.chat_with_tools = AsyncMock(
            return_value=LLMCallResult(
                text='{"summary": "User asked 10 questions.", "current_state": {}}',
                usage=TokenUsage(input_tokens=100, output_tokens=50),
            )
        )

        await maybe_create_checkpoint(
            thread_id=thread_id,
            tenant_id=t.id,
            channel=ConversationChannel.WEB,
            llm=mock_llm,
            uow=uow,
        )
        await uow.commit()

        mock_llm.chat_with_tools.assert_called_once()

        # Verify checkpoint message was saved
        all_msgs = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        checkpoints = [m for m in all_msgs if m.is_checkpoint]
        assert len(checkpoints) == 1
        assert "User asked 10 questions" in checkpoints[0].content


def test_build_summarizer_input_truncates() -> None:
    """Long message lists are truncated to _MAX_RECENT_MESSAGES."""
    messages = []
    for i in range(40):
        m = MagicMock()
        m.is_checkpoint = False
        m.role = "user"
        m.content = f"msg {i}"
        m.tool_data = None
        messages.append(m)

    result = _build_summarizer_input(messages)
    assert "older messages omitted" in result


def test_build_summarizer_input_includes_checkpoint() -> None:
    """Previous checkpoint state is included in the input."""
    checkpoint = MagicMock()
    checkpoint.is_checkpoint = True
    checkpoint.content = "previous state summary"
    checkpoint.tool_data = [{"checkpoint": {"summary": "old"}}]

    recent = MagicMock()
    recent.is_checkpoint = False
    recent.role = "user"
    recent.content = "new question"
    recent.tool_data = None

    result = _build_summarizer_input([checkpoint, recent])
    assert "previous state summary" in result
    assert "new question" in result
