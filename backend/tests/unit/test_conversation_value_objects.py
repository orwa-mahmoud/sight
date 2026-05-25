"""Unit tests for conversation value objects."""

from __future__ import annotations

from src.domain.conversations.value_objects import ConversationChannel, ConversationRole


def test_conversation_channel_values() -> None:
    assert ConversationChannel.WHATSAPP == "whatsapp"
    assert ConversationChannel.TELEGRAM == "telegram"
    assert ConversationChannel.EMAIL == "email"
    assert ConversationChannel.WEB == "web"
    assert ConversationChannel.OWNER_DASHBOARD == "owner_dashboard"
    assert ConversationChannel.API == "api"


def test_conversation_role_values() -> None:
    assert ConversationRole.USER == "user"
    assert ConversationRole.ASSISTANT == "assistant"
    assert ConversationRole.SYSTEM == "system"
    assert ConversationRole.TOOL == "tool"
