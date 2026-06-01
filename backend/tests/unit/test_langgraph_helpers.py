"""Unit tests for LangGraph infrastructure helpers."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.ai.types import ToolDef
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole, LLMToolCall
from src.infrastructure.ai.graph import (
    _FALLBACK_REPLY,
    _final_reply_text,
    _from_lc_messages,
    _to_ai_message,
    _to_lc_messages,
    _to_openai_schema,
)


def test_final_reply_text_returns_assistant_content() -> None:
    msgs = [HumanMessage(content="hi"), AIMessage(content="Hello there!")]
    assert _final_reply_text(msgs) == "Hello there!"


def test_final_reply_text_falls_back_on_empty_messages() -> None:
    assert _final_reply_text([]) == _FALLBACK_REPLY


def test_final_reply_text_falls_back_when_last_message_is_blank() -> None:
    # Iteration cap hit: the final AI message still carries tool calls and the
    # content is empty — the asker must not receive a blank reply.
    msgs = [
        HumanMessage(content="do something"),
        AIMessage(content="", tool_calls=[{"name": "search_documents", "args": {}, "id": "t1"}]),
    ]
    assert _final_reply_text(msgs) == _FALLBACK_REPLY


def test_final_reply_text_falls_back_on_whitespace_only() -> None:
    msgs = [AIMessage(content="   \n  ")]
    assert _final_reply_text(msgs) == _FALLBACK_REPLY


def test_final_reply_text_coerces_non_string_content() -> None:
    # LangChain can carry list-style content blocks; they must stringify, not crash.
    msgs = [AIMessage(content=[{"type": "text", "text": "block"}])]
    result = _final_reply_text(msgs)
    assert isinstance(result, str)
    assert result != _FALLBACK_REPLY


def test_to_lc_messages_all_roles() -> None:
    msgs = [
        LLMMessage(role=LLMMessageRole.SYSTEM, content="sys"),
        LLMMessage(role=LLMMessageRole.USER, content="user"),
        LLMMessage(role=LLMMessageRole.ASSISTANT, content="asst"),
        LLMMessage(role=LLMMessageRole.TOOL, content="tool", tool_call_id="tc1"),
    ]
    lc = _to_lc_messages(msgs)
    assert isinstance(lc[0], SystemMessage)
    assert isinstance(lc[1], HumanMessage)
    assert isinstance(lc[2], AIMessage)
    assert isinstance(lc[3], ToolMessage)
    assert lc[3].tool_call_id == "tc1"


def test_from_lc_messages_round_trip() -> None:
    lc = [
        SystemMessage(content="s"),
        HumanMessage(content="h"),
        AIMessage(content="a"),
        ToolMessage(content="t", tool_call_id="x"),
    ]
    domain = _from_lc_messages(lc)
    assert domain[0].role == LLMMessageRole.SYSTEM
    assert domain[1].role == LLMMessageRole.USER
    assert domain[2].role == LLMMessageRole.ASSISTANT
    assert domain[3].role == LLMMessageRole.TOOL
    assert domain[3].tool_call_id == "x"


def test_to_ai_message_with_tool_calls() -> None:
    tc = LLMToolCall(id="c1", name="search", arguments={"q": "test"})
    msg = _to_ai_message("", (tc,))
    assert isinstance(msg, AIMessage)
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0]["name"] == "search"


def test_to_ai_message_text_only() -> None:
    msg = _to_ai_message("Hello!", ())
    assert isinstance(msg, AIMessage)
    assert msg.content == "Hello!"
    assert not msg.tool_calls


def test_to_openai_schema() -> None:
    schema = _to_openai_schema(ToolDef(name="t", description="d", parameters_schema={"type": "object"}))
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "t"
