"""Unit tests for the Telegram webhook handler with mocked gateway."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_telegram_webhook_no_message_returns_200() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/webhooks/{uuid4()}/telegram",
            json={"update_id": 123},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_webhook_invalid_tenant_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhooks/not-a-uuid/telegram",
            json={"message": {"from": {"id": 1}, "text": "hi", "chat": {"id": 1}}},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_telegram_webhook_empty_text_returns_200() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/webhooks/{uuid4()}/telegram",
            json={"message": {"from": {"id": 1}, "text": "", "chat": {"id": 1}}},
        )
    assert resp.status_code == 200
