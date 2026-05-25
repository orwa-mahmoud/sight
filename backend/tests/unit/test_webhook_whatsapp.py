"""Unit tests for WhatsApp webhook handler + helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.drivers.api.webhooks.whatsapp import _check_signature, _extract_message, _parse_tenant_id
from src.main import app


def test_parse_tenant_id_valid() -> None:
    tid = uuid4()
    assert _parse_tenant_id(str(tid)) == tid


def test_parse_tenant_id_invalid() -> None:
    assert _parse_tenant_id("not-a-uuid") is None


def test_extract_message_empty_payload() -> None:
    text, phone, _name, _pnid = _extract_message({})
    assert text == ""
    assert phone == ""


def test_extract_message_text_message() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [{"from": "+123", "type": "text", "text": {"body": "Hello"}}],
                            "contacts": [{"profile": {"name": "Sara"}}],
                            "metadata": {"phone_number_id": "pn123"},
                        }
                    }
                ]
            }
        ]
    }
    text, phone, name, pnid = _extract_message(payload)
    assert text == "Hello"
    assert phone == "+123"
    assert name == "Sara"
    assert pnid == "pn123"


def test_extract_message_non_text_type() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [{"from": "+123", "type": "image"}],
                        }
                    }
                ]
            }
        ]
    }
    text, _phone, _name, _pnid = _extract_message(payload)
    assert text == ""


def test_check_signature_no_access_token() -> None:
    config = MagicMock()
    config.whatsapp_access_token = ""
    assert _check_signature(b"body", None, config) is True


def test_check_signature_no_verify_token() -> None:
    config = MagicMock()
    config.whatsapp_access_token = "token"
    config.whatsapp_verify_token = ""
    assert _check_signature(b"body", None, config) is True


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
async def test_whatsapp_webhook_no_messages_returns_200() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/webhooks/{uuid4()}/whatsapp",
            json={"entry": [{"changes": [{"value": {"messages": []}}]}]},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_whatsapp_webhook_invalid_tenant_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhooks/bad-uuid/whatsapp",
            json={
                "entry": [
                    {"changes": [{"value": {"messages": [{"from": "x", "type": "text", "text": {"body": "hi"}}]}}]}
                ]
            },
        )
    assert resp.status_code == 400
