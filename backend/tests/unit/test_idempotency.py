"""Unit tests for webhook message de-duplication."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.infrastructure.channels.idempotency import is_duplicate_message
from src.infrastructure.channels.telegram import TelegramAdapter
from src.infrastructure.channels.whatsapp import WhatsAppAdapter


@pytest.mark.asyncio
async def test_whatsapp_parse_captures_wamid() -> None:
    adapter = WhatsAppAdapter(phone_number_id="p", access_token="t")
    payload: dict[str, Any] = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [{"id": "wamid.ABC", "from": "123", "type": "text", "text": {"body": "hi"}}]
                        }
                    }
                ]
            }
        ]
    }
    incoming = await adapter.parse_incoming(payload)
    assert incoming.message_id == "wamid.ABC"


@pytest.mark.asyncio
async def test_telegram_parse_builds_chat_qualified_id() -> None:
    adapter = TelegramAdapter()
    payload: dict[str, Any] = {
        "message": {"message_id": 42, "from": {"id": 7, "first_name": "S"}, "chat": {"id": 99}, "text": "hi"}
    }
    incoming = await adapter.parse_incoming(payload)
    assert incoming.message_id == "99:42"


@pytest.mark.asyncio
async def test_empty_message_id_is_never_duplicate() -> None:
    # No id to key on (some payloads) -> always process.
    assert await is_duplicate_message(tenant_id=uuid4(), channel="whatsapp", message_id="") is False


@pytest.mark.asyncio
async def test_first_delivery_processes_then_repeat_is_duplicate() -> None:
    client = AsyncMock()
    # SET NX returns truthy when newly set, None when the key already existed.
    client.set = AsyncMock(side_effect=["OK", None])
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=client):
        tid = uuid4()
        first = await is_duplicate_message(tenant_id=tid, channel="whatsapp", message_id="wamid.1")
        second = await is_duplicate_message(tenant_id=tid, channel="whatsapp", message_id="wamid.1")
    assert first is False
    assert second is True


@pytest.mark.asyncio
async def test_no_redis_degrades_to_not_duplicate() -> None:
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=None):
        assert await is_duplicate_message(tenant_id=uuid4(), channel="telegram", message_id="99:1") is False


@pytest.mark.asyncio
async def test_redis_error_degrades_to_not_duplicate() -> None:
    client = AsyncMock()
    client.set = AsyncMock(side_effect=RuntimeError("redis down"))
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=client):
        assert await is_duplicate_message(tenant_id=uuid4(), channel="whatsapp", message_id="wamid.x") is False
