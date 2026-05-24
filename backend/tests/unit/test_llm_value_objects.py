"""Unit tests for LLM domain value objects."""

from __future__ import annotations

from src.domain.llm.value_objects import LLMCallResult, LLMMessage, LLMMessageRole, LLMToolCall, TokenUsage


def test_token_usage_total() -> None:
    u = TokenUsage(input_tokens=100, output_tokens=50, cache_read_tokens=30)
    assert u.total == 180


def test_llm_message_construction() -> None:
    msg = LLMMessage(role=LLMMessageRole.USER, content="Hello")
    assert msg.role == LLMMessageRole.USER
    assert msg.tool_calls == ()


def test_llm_tool_call() -> None:
    tc = LLMToolCall(id="call_1", name="search", arguments={"q": "test"})
    assert tc.name == "search"


def test_llm_call_result_defaults() -> None:
    r = LLMCallResult(text="reply")
    assert r.tool_calls == ()
    assert r.usage.total == 0
    assert r.provider == ""
