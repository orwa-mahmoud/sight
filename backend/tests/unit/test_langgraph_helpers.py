"""Unit tests for LangGraph infrastructure helpers."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.ai.types import ToolDef
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole, LLMToolCall
from src.infrastructure.ai.graph import _from_lc_messages, _to_ai_message, _to_lc_messages, _to_openai_schema


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
