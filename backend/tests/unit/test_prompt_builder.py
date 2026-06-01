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


def test_asker_prompt_includes_bot_name() -> None:
    msg = build_asker_system_prompt(bot_name="Aria")
    assert "You are Aria" in msg.content


def test_asker_prompt_defaults_to_configured_language() -> None:
    msg = build_asker_system_prompt(bot_language="Arabic")
    assert "Default to responding in Arabic" in msg.content
    assert "match the asker's language" in msg.content


def test_asker_prompt_without_language_matches_asker() -> None:
    msg = build_asker_system_prompt()
    assert "Match the language the asker uses" in msg.content


def test_asker_prompt_reflects_welcome_message_tone() -> None:
    msg = build_asker_system_prompt(welcome_message="Hey there! 👋 How can I help?")
    assert "Hey there!" in msg.content


def test_asker_prompt_ignores_blank_personalization() -> None:
    # Whitespace-only config must not inject a bot name or a configured language.
    msg = build_asker_system_prompt(bot_name="   ", bot_language="  ")
    assert "You are an AI front desk assistant." in msg.content
    assert "Match the language the asker uses" in msg.content
