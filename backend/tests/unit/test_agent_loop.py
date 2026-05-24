"""Unit tests for the agent loop — mocked LLM, real tool dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.ai.agents.agent import _to_openai_schema, run_agent_loop
from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF
from src.ai.types import ToolDef
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.llm.value_objects import LLMCallResult, LLMMessage, LLMMessageRole, LLMToolCall, TokenUsage


@pytest.mark.asyncio
async def test_agent_returns_text_when_no_tool_calls() -> None:
    mock_llm = AsyncMock()
    mock_llm.chat_with_tools.return_value = LLMCallResult(
        text="Hello! How can I help?",
        usage=TokenUsage(input_tokens=10, output_tokens=5),
        provider="openai",
        model="gpt-4o-mini",
    )
    result = await run_agent_loop(
        messages=[LLMMessage(role=LLMMessageRole.USER, content="Hi")],
        tools=[SEARCH_DOCUMENTS_DEF],
        llm=mock_llm,
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        conversation_id=None,
        asker_name=None,
        asker_contact=None,
        retriever=AsyncMock(),
        uow=MagicMock(),
    )
    assert result.text == "Hello! How can I help?"
    assert result.tool_calls == []
    assert result.input_tokens == 10
    assert result.output_tokens == 5


@pytest.mark.asyncio
async def test_agent_calls_search_then_responds() -> None:
    mock_llm = AsyncMock()
    # First call: LLM wants to use search_documents
    mock_llm.chat_with_tools.side_effect = [
        LLMCallResult(
            text="",
            tool_calls=(LLMToolCall(id="call_1", name="search_documents", arguments={"query": "office hours"}),),
            usage=TokenUsage(input_tokens=20, output_tokens=10),
        ),
        # Second call: LLM responds with text after seeing tool result
        LLMCallResult(
            text="We're open 9-5!",
            usage=TokenUsage(input_tokens=30, output_tokens=8),
        ),
    ]
    mock_retriever = AsyncMock()
    mock_retriever.hybrid_retrieve.return_value = []

    result = await run_agent_loop(
        messages=[LLMMessage(role=LLMMessageRole.USER, content="When are you open?")],
        tools=[SEARCH_DOCUMENTS_DEF],
        llm=mock_llm,
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        conversation_id=None,
        asker_name=None,
        asker_contact=None,
        retriever=mock_retriever,
        uow=MagicMock(),
    )
    assert result.text == "We're open 9-5!"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "search_documents"
    assert result.input_tokens == 50
    assert result.output_tokens == 18


def test_to_openai_schema() -> None:
    schema = _to_openai_schema(ToolDef(name="test", description="A test tool", parameters_schema={"type": "object"}))
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test"
    assert schema["function"]["description"] == "A test tool"
