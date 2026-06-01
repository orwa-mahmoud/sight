"""Tests for the LangGraph state graph execution with mocked LLM."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.llm.value_objects import LLMCallResult, LLMMessage, LLMMessageRole, LLMToolCall, TokenUsage
from src.infrastructure.ai.graph import build_agent_graph, run_graph


@pytest.mark.asyncio
async def test_graph_text_only_response() -> None:
    """Graph with no tool calls — single LLM round."""
    mock_llm = AsyncMock()
    mock_llm.chat_with_tools = AsyncMock(
        return_value=LLMCallResult(
            text="Hello!",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )
    )
    graph = build_agent_graph(
        llm=mock_llm,
        tools=[SEARCH_DOCUMENTS_DEF],
        retriever=AsyncMock(),
        uow=AsyncMock(),
    )
    result = await run_graph(
        graph,
        messages=[LLMMessage(role=LLMMessageRole.USER, content="Hi")],
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        conversation_id=None,
        contact_id=None,
    )
    assert result.text == "Hello!"
    assert result.tool_calls == []
    assert result.input_tokens == 10


@pytest.mark.asyncio
async def test_dispatch_key_fact_requires_resolved_contact() -> None:
    """save_key_fact/remove_key_fact must no-op with an error when contact is unresolved."""
    from src.infrastructure.ai.graph import _dispatch_tool

    result = await _dispatch_tool(
        tool_name="save_key_fact",
        arguments={"key": "name", "value": "Sam"},
        tenant_id=uuid4(),
        channel=ConversationChannel.API,
        conversation_id=None,
        contact_id=None,
        retriever=AsyncMock(),
        uow=AsyncMock(),
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_graph_forwards_temperature_and_max_tokens() -> None:
    """The tenant's configured temperature + max_tokens must reach the LLM call."""
    mock_llm = AsyncMock()
    mock_llm.chat_with_tools = AsyncMock(
        return_value=LLMCallResult(text="ok", usage=TokenUsage(input_tokens=1, output_tokens=1))
    )
    graph = build_agent_graph(
        llm=mock_llm,
        tools=[SEARCH_DOCUMENTS_DEF],
        retriever=AsyncMock(),
        uow=AsyncMock(),
        max_tokens=777,
        temperature=0.9,
    )
    await run_graph(
        graph,
        messages=[LLMMessage(role=LLMMessageRole.USER, content="Hi")],
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        conversation_id=None,
        contact_id=None,
    )
    _, kwargs = mock_llm.chat_with_tools.call_args
    assert kwargs["max_tokens"] == 777
    assert kwargs["temperature"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_graph_with_tool_call() -> None:
    """Graph calls search_documents then responds with text."""
    mock_llm = AsyncMock()
    mock_llm.chat_with_tools = AsyncMock(
        side_effect=[
            LLMCallResult(
                text="",
                tool_calls=(LLMToolCall(id="c1", name="search_documents", arguments={"query": "hours"}),),
                usage=TokenUsage(input_tokens=20, output_tokens=10),
            ),
            LLMCallResult(
                text="We're open 9-5!",
                usage=TokenUsage(input_tokens=30, output_tokens=8),
            ),
        ]
    )
    mock_retriever = AsyncMock()
    mock_retriever.hybrid_retrieve = AsyncMock(return_value=[])

    graph = build_agent_graph(
        llm=mock_llm,
        tools=[SEARCH_DOCUMENTS_DEF],
        retriever=mock_retriever,
        uow=AsyncMock(),
    )
    result = await run_graph(
        graph,
        messages=[LLMMessage(role=LLMMessageRole.USER, content="When open?")],
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        conversation_id=None,
        contact_id=None,
    )
    assert result.text == "We're open 9-5!"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "search_documents"
    assert result.input_tokens == 50


@pytest.mark.asyncio
async def test_graph_unknown_tool_returns_error() -> None:
    """Unknown tool name returns error dict, doesn't crash."""
    mock_llm = AsyncMock()
    mock_llm.chat_with_tools = AsyncMock(
        side_effect=[
            LLMCallResult(
                text="",
                tool_calls=(LLMToolCall(id="c1", name="nonexistent_tool", arguments={}),),
                usage=TokenUsage(input_tokens=10, output_tokens=5),
            ),
            LLMCallResult(
                text="Sorry, something went wrong.",
                usage=TokenUsage(input_tokens=20, output_tokens=8),
            ),
        ]
    )
    graph = build_agent_graph(
        llm=mock_llm,
        tools=[SEARCH_DOCUMENTS_DEF],
        retriever=AsyncMock(),
        uow=AsyncMock(),
    )
    result = await run_graph(
        graph,
        messages=[LLMMessage(role=LLMMessageRole.USER, content="test")],
        tenant_id=uuid4(),
        channel=ConversationChannel.WEB,
        conversation_id=None,
        contact_id=None,
    )
    assert "nonexistent_tool" in str(result.tool_calls[0].result)
