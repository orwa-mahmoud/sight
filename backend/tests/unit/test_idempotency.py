"""Unit tests for webhook message de-duplication."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.infrastructure.channels.idempotency import mark_message_processed, was_message_processed
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
async def test_empty_message_id_is_never_seen() -> None:
    # No id to key on (some payloads) -> always process, never mark.
    assert await was_message_processed(tenant_id=uuid4(), channel="whatsapp", message_id="") is False


@pytest.mark.asyncio
async def test_unmarked_message_is_not_seen_then_marked_is_seen() -> None:
    store: dict[str, str] = {}

    async def _get(key: str) -> str | None:
        return store.get(key)

    async def _set(key: str, val: str, ex: int | None = None) -> None:
        store[key] = val

    client = AsyncMock()
    client.get = AsyncMock(side_effect=_get)
    client.set = AsyncMock(side_effect=_set)
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=client):
        tid = uuid4()
        # Not processed yet → False; only after marking on success → True.
        assert await was_message_processed(tenant_id=tid, channel="whatsapp", message_id="wamid.1") is False
        await mark_message_processed(tenant_id=tid, channel="whatsapp", message_id="wamid.1")
        assert await was_message_processed(tenant_id=tid, channel="whatsapp", message_id="wamid.1") is True


@pytest.mark.asyncio
async def test_mark_with_empty_message_id_is_noop() -> None:
    client = AsyncMock()
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=client):
        await mark_message_processed(tenant_id=uuid4(), channel="whatsapp", message_id="")
    client.set.assert_not_called()


@pytest.mark.asyncio
async def test_no_redis_degrades_to_not_seen() -> None:
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=None):
        assert await was_message_processed(tenant_id=uuid4(), channel="telegram", message_id="99:1") is False
        await mark_message_processed(tenant_id=uuid4(), channel="telegram", message_id="99:1")  # no-op, no raise


@pytest.mark.asyncio
async def test_redis_error_on_check_degrades_to_not_seen() -> None:
    client = AsyncMock()
    client.get = AsyncMock(side_effect=RuntimeError("redis down"))
    with patch("src.infrastructure.channels.idempotency._get_client", return_value=client):
        assert await was_message_processed(tenant_id=uuid4(), channel="whatsapp", message_id="wamid.x") is False
