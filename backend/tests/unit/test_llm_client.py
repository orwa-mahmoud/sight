"""Unit tests for the LangChain LLM client — chat_with_tools + translation helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.llm.value_objects import LLMCallResult, LLMMessage, LLMMessageRole, LLMToolCall, TokenUsage
from src.infrastructure.llm.client import _to_call_result, _to_lc_message

# ── _to_lc_message tests ────────────────────────────────────────


def test_to_lc_message_system() -> None:
    msg = LLMMessage(role=LLMMessageRole.SYSTEM, content="You are helpful.")
    result = _to_lc_message(msg)
    assert result.__class__.__name__ == "SystemMessage"
    assert result.content == "You are helpful."


def test_to_lc_message_user() -> None:
    msg = LLMMessage(role=LLMMessageRole.USER, content="Hello")
    result = _to_lc_message(msg)
    assert result.__class__.__name__ == "HumanMessage"
    assert result.content == "Hello"


def test_to_lc_message_assistant() -> None:
    msg = LLMMessage(role=LLMMessageRole.ASSISTANT, content="Hi there")
    result = _to_lc_message(msg)
    assert result.__class__.__name__ == "AIMessage"
    assert result.content == "Hi there"


def test_to_lc_message_tool() -> None:
    msg = LLMMessage(role=LLMMessageRole.TOOL, content='{"result": 42}', tool_call_id="call_123")
    result = _to_lc_message(msg)
    assert result.__class__.__name__ == "ToolMessage"
    assert result.content == '{"result": 42}'
    assert result.tool_call_id == "call_123"


def test_to_lc_message_tool_missing_call_id() -> None:
    msg = LLMMessage(role=LLMMessageRole.TOOL, content="ok")
    result = _to_lc_message(msg)
    assert result.tool_call_id == ""


# ── _to_call_result tests ───────────────────────────────────────


def test_to_call_result_text_only() -> None:
    response = MagicMock()
    response.content = "Hello!"
    response.tool_calls = []
    response.usage_metadata = {"input_tokens": 10, "output_tokens": 5}

    result = _to_call_result(response, provider="openai", model="gpt-4o")
    assert isinstance(result, LLMCallResult)
    assert result.text == "Hello!"
    assert result.tool_calls == ()
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5
    assert result.provider == "openai"
    assert result.model == "gpt-4o"


def test_to_call_result_with_tool_calls() -> None:
    response = MagicMock()
    response.content = ""
    response.tool_calls = [
        {"id": "call_1", "name": "search", "args": {"query": "hello"}},
        {"id": "call_2", "name": "lookup", "args": {}},
    ]
    response.usage_metadata = {"input_tokens": 20, "output_tokens": 10}

    result = _to_call_result(response, provider="anthropic", model="claude-3")
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0] == LLMToolCall(id="call_1", name="search", arguments={"query": "hello"})
    assert result.tool_calls[1] == LLMToolCall(id="call_2", name="lookup", arguments={})


def test_to_call_result_non_string_content() -> None:
    response = MagicMock()
    response.content = [{"type": "text", "text": "hello"}]  # non-string content
    response.tool_calls = []
    response.usage_metadata = {}

    result = _to_call_result(response, provider="openai", model="gpt-4o")
    assert result.text == ""  # non-string falls back to empty


def test_to_call_result_no_usage_metadata() -> None:
    response = MagicMock(spec=[])  # no attributes
    response.content = "Ok"
    response.tool_calls = None

    result = _to_call_result(response, provider="openai", model="gpt-4o")
    assert result.usage == TokenUsage(input_tokens=0, output_tokens=0)


def test_to_call_result_with_cache_read_tokens() -> None:
    response = MagicMock()
    response.content = "cached"
    response.tool_calls = []
    response.usage_metadata = {
        "input_tokens": 100,
        "output_tokens": 50,
        "input_token_details": {"cache_read": 80},
    }

    result = _to_call_result(response, provider="anthropic", model="claude-3")
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50
    assert result.usage.cache_read_tokens == 80


def test_to_call_result_tool_calls_with_missing_fields() -> None:
    response = MagicMock()
    response.content = ""
    response.tool_calls = [
        {"id": None, "name": None, "args": None},  # all None
    ]
    response.usage_metadata = {}

    result = _to_call_result(response, provider="openai", model="gpt-4o")
    assert result.tool_calls[0] == LLMToolCall(id="", name="", arguments={})


# ── chat_with_tools integration (mock init_chat_model) ───────────


@pytest.mark.asyncio
@patch("src.infrastructure.llm.client.init_chat_model")
async def test_chat_with_tools_basic(mock_init: MagicMock) -> None:
    mock_chat = AsyncMock()
    response = MagicMock()
    response.content = "I can help with that."
    response.tool_calls = []
    response.usage_metadata = {"input_tokens": 15, "output_tokens": 8}
    mock_chat.ainvoke = AsyncMock(return_value=response)
    mock_init.return_value = mock_chat

    from src.infrastructure.llm.client import LangChainLLMClient

    client = LangChainLLMClient(provider="openai", model="gpt-4o", api_key="sk-test")

    messages = [
        LLMMessage(role=LLMMessageRole.SYSTEM, content="Be helpful"),
        LLMMessage(role=LLMMessageRole.USER, content="Hi"),
    ]
    result = await client.chat_with_tools(messages)

    assert result.text == "I can help with that."
    assert result.usage.input_tokens == 15
    mock_chat.ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("src.infrastructure.llm.client.init_chat_model")
async def test_chat_with_tools_binds_params(mock_init: MagicMock) -> None:
    mock_chat = MagicMock()
    bound_chat = AsyncMock()
    response = MagicMock()
    response.content = "Ok"
    response.tool_calls = []
    response.usage_metadata = {}
    bound_chat.ainvoke = AsyncMock(return_value=response)
    # .bind() returns a new chat, then .bind_tools() on that returns another
    tools_chat = AsyncMock()
    tools_chat.ainvoke = AsyncMock(return_value=response)
    bound_chat.bind_tools = MagicMock(return_value=tools_chat)
    mock_chat.bind = MagicMock(return_value=bound_chat)
    mock_init.return_value = mock_chat

    from src.infrastructure.llm.client import LangChainLLMClient

    client = LangChainLLMClient(provider="openai", model="gpt-4o")

    tools = [{"type": "function", "function": {"name": "search"}}]
    messages = [LLMMessage(role=LLMMessageRole.USER, content="Search for X")]
    result = await client.chat_with_tools(
        messages,
        tools=tools,
        max_tokens=500,
        temperature=0.7,
    )

    mock_chat.bind.assert_called_once_with(max_tokens=500, temperature=0.7)
    bound_chat.bind_tools.assert_called_once()
    assert result.text == "Ok"
