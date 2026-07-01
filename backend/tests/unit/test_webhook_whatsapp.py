"""Unit tests for WhatsApp webhook handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.drivers.api.webhooks.whatsapp import _handle_whatsapp_post, _parse_tenant_id, _verify_token_matches
from src.infrastructure.channels.whatsapp import WhatsAppAdapter
from src.main import app


def test_parse_tenant_id_valid() -> None:
    tid = uuid4()
    assert _parse_tenant_id(str(tid)) == tid


def test_parse_tenant_id_invalid() -> None:
    assert _parse_tenant_id("not-a-uuid") is None


def test_verify_token_matches() -> None:
    assert _verify_token_matches("abc", "abc") is True
    assert _verify_token_matches("abc", "xyz") is False
    assert _verify_token_matches("abc", None) is False
    assert _verify_token_matches("", "abc") is False
    assert _verify_token_matches("abc", "") is False


def test_verify_signature_valid() -> None:
    import hashlib
    import hmac

    secret = "test-app-secret"
    body = b'{"test": "data"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert WhatsAppAdapter.verify_signature(body, sig, secret) is True


def test_verify_signature_invalid() -> None:
    assert WhatsAppAdapter.verify_signature(b"data", "sha256=wrong", "secret") is False


def test_verify_signature_missing_header() -> None:
    assert WhatsAppAdapter.verify_signature(b"data", "", "secret") is False


def test_verify_signature_missing_secret() -> None:
    assert WhatsAppAdapter.verify_signature(b"data", "sha256=abc", "") is False


@pytest.mark.asyncio
async def test_whatsapp_verify_invalid_returns_403() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/webhooks/{uuid4()}/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "ch"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_whatsapp_webhook_invalid_tenant_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhooks/bad-uuid/whatsapp",
            json={"entry": [{"changes": [{"value": {"messages": []}}]}]},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_whatsapp_processing_failure_returns_503_and_does_not_mark_seen() -> None:
    """A transient agent failure must ask Meta to redeliver (503), not ack 200, and
    must NOT mark the message processed — so the retry can reprocess it."""
    tid = uuid4()
    config = MagicMock()
    config.whatsapp_phone_number_id = "pnid"
    config.whatsapp_access_token = "tok"

    mock_uow = MagicMock()
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    adapter = MagicMock()
    incoming = MagicMock()
    incoming.sender_phone = "+123"
    incoming.text = "hello"
    incoming.message_id = "wamid.ABC"
    adapter.parse_incoming = AsyncMock(return_value=incoming)
    adapter.send_text = AsyncMock()

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.whatsapp.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.whatsapp.UnitOfWork", return_value=mock_uow),
        patch(
            "src.drivers.api.webhooks.whatsapp._validate_whatsapp_request",
            new_callable=AsyncMock,
            return_value=config,
        ),
        patch("src.drivers.api.webhooks.whatsapp.get_whatsapp_adapter", new_callable=AsyncMock, return_value=adapter),
        patch("src.drivers.api.webhooks.whatsapp.was_message_processed", new_callable=AsyncMock, return_value=False),
        patch("src.drivers.api.webhooks.whatsapp.mark_message_processed", new_callable=AsyncMock) as mock_mark,
        patch(
            "src.drivers.api.webhooks.whatsapp.chat_with_agent",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM down"),
        ),
    ):
        status = await _handle_whatsapp_post(tid, b"{}", {}, "sig", str(tid))

    assert status == 503
    mock_uow.rollback.assert_awaited_once()
    mock_mark.assert_not_called()  # un-marked → the redelivery reprocesses
