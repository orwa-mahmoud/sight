"""Unit tests for system prompt builder."""

from __future__ import annotations

from src.ai.context.prompts import build_asker_system_prompt
from src.domain.llm.value_objects import LLMMessageRole


def test_asker_prompt_is_system_role() -> None:
    msg = build_asker_system_prompt()
    assert msg.role == LLMMessageRole.SYSTEM


def test_asker_prompt_mentions_search_documents() -> None:
    msg = build_asker_system_prompt()
    assert "search_documents" in msg.content


def test_asker_prompt_mentions_escalate() -> None:
    msg = build_asker_system_prompt()
    assert "escalate" in msg.content.lower()
