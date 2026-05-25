"""Integration tests for the settings routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.asyncio
async def test_get_settings(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "llm_provider" in body
    assert "bot_name" in body


@pytest.mark.asyncio
async def test_update_llm(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "gpt-4o", "max_tokens": 2048, "temperature": 0.5},
    )
    assert resp.status_code == 200
    assert resp.json()["llm_model"] == "gpt-4o"
    assert resp.json()["llm_max_tokens"] == 2048


@pytest.mark.asyncio
async def test_update_embedding(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/embedding",
        headers={"Authorization": f"Bearer {token}"},
        json={"model": "text-embedding-3-small", "dimensions": 512},
    )
    assert resp.status_code == 200
    assert resp.json()["embedding_model"] == "text-embedding-3-small"


@pytest.mark.asyncio
async def test_update_whatsapp(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/whatsapp",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone_number_id": "12345", "access_token": "EAA-secret", "verify_token": "vt-secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["whatsapp_phone_number_id"] == "12345"


@pytest.mark.asyncio
async def test_update_telegram(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/telegram",
        headers={"Authorization": f"Bearer {token}"},
        json={"bot_token": "123:ABC", "webhook_secret": "ws-secret"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_bot(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/settings/bot",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "FD Bot", "welcome_message": "Hi!", "language": "en"},
    )
    assert resp.status_code == 200
    assert resp.json()["bot_name"] == "FD Bot"


@pytest.mark.asyncio
async def test_settings_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 401
