"""Unit tests for src/infrastructure/channels/api.py -- DirectAPIAdapter."""

from __future__ import annotations

import pytest

from src.infrastructure.channels.api import DirectAPIAdapter
from src.infrastructure.channels.base import MessageType


class TestDirectAPIAdapterInit:
    def test_channel_name(self) -> None:
        adapter = DirectAPIAdapter()
        assert adapter.channel_name == "api"


class TestParseIncoming:
    @pytest.mark.asyncio
    async def test_full_payload(self) -> None:
        adapter = DirectAPIAdapter()
        payload = {"user_phone": "+971", "message": "Hello", "thread_id": "t-1"}
        incoming = await adapter.parse_incoming(payload)
        assert incoming.channel == "api"
        assert incoming.sender_phone == "+971"
        assert incoming.text == "Hello"
        assert incoming.thread_id == "t-1"
        assert incoming.message_type == MessageType.TEXT
        assert incoming.raw_payload == payload

    @pytest.mark.asyncio
    async def test_empty_payload(self) -> None:
        adapter = DirectAPIAdapter()
        incoming = await adapter.parse_incoming({})
        assert incoming.sender_phone == ""
        assert incoming.text == ""
        assert incoming.thread_id == ""

    @pytest.mark.asyncio
    async def test_missing_keys_default_empty(self) -> None:
        adapter = DirectAPIAdapter()
        incoming = await adapter.parse_incoming({"extra": "val"})
        assert incoming.sender_phone == ""
        assert incoming.text == ""


class TestSendText:
    @pytest.mark.asyncio
    async def test_noop(self) -> None:
        adapter = DirectAPIAdapter()
        result = await adapter.send_text("+1", "Hello world")
        # No-op: returns None
        assert result is None


class TestSendVoice:
    @pytest.mark.asyncio
    async def test_noop(self) -> None:
        adapter = DirectAPIAdapter()
        # Should not raise
        await adapter.send_voice("+1", b"audio-data", "audio/ogg")
