"""Unit tests for AI orchestration types."""

from __future__ import annotations

from uuid import uuid4

from src.ai.types import AgentLoopResult, ChatInput, ChatResult, ToolCallResult, ToolDef
from src.domain.conversations.value_objects import ConversationChannel


def test_chat_input_construction() -> None:
    inp = ChatInput(
        message="hello",
        tenant_id=uuid4(),
        channel=ConversationChannel.WHATSAPP,
        sender_identifier="+971500000000",
    )
    assert inp.thread_id is None
    assert inp.sender_name is None


def test_chat_result() -> None:
    r = ChatResult(response="Hi", thread_id="t1")
    assert not r.escalated
    assert r.request_id == ""


def test_tool_def() -> None:
    t = ToolDef(name="search", description="Search docs", parameters_schema={"type": "object"})
    assert t.name == "search"


def test_tool_call_result() -> None:
    tc = ToolCallResult(tool_name="search", arguments={"q": "x"}, result={"hits": []})
    assert tc.summary == ""


def test_agent_loop_result_defaults() -> None:
    r = AgentLoopResult(text="done")
    assert r.tool_calls == []
    assert r.input_tokens == 0
