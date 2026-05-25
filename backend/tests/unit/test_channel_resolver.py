"""Tests for channel resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.conversations.value_objects import ConversationChannel
from src.infrastructure.channels.channel_resolver import relay_question_reply


@pytest.mark.asyncio
async def test_relay_no_contact():
    config = MagicMock()
    result = await relay_question_reply(
        channel=ConversationChannel.WHATSAPP,
        asker_contact=None,
        reply_text="answer",
        tenant_config=config,
    )
    assert result is False


@pytest.mark.asyncio
async def test_relay_whatsapp_not_configured():
    config = MagicMock()
    config.whatsapp_access_token = ""
    config.whatsapp_phone_number_id = ""
    config.telegram_bot_token = ""
    result = await relay_question_reply(
        channel=ConversationChannel.WHATSAPP,
        asker_contact="+123",
        reply_text="answer",
        tenant_config=config,
    )
    assert result is False
