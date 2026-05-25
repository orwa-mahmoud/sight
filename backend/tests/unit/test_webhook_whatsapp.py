"""Unit tests for WhatsApp webhook handler."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.drivers.api.webhooks.whatsapp import _parse_tenant_id
from src.infrastructure.channels.whatsapp import WhatsAppAdapter
from src.main import app


def test_parse_tenant_id_valid() -> None:
    tid = uuid4()
    assert _parse_tenant_id(str(tid)) == tid


def test_parse_tenant_id_invalid() -> None:
    assert _parse_tenant_id("not-a-uuid") is None


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
