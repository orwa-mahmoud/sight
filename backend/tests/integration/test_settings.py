"""Integration tests for the tenant settings API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_settings_returns_masked_keys(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "openai"
    assert body["llm_model"] == "gpt-4o-mini"
    assert body["llm_api_key_masked"] == ""  # empty key masking
    assert body["bot_name"] == "Front Desk Assistant"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_llm_config(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/api/v1/settings/llm",
        json={"provider": "anthropic", "model": "claude-sonnet-4-5", "api_key": "sk-ant-test1234567890"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm_provider"] == "anthropic"
    assert body["llm_model"] == "claude-sonnet-4-5"
    assert body["llm_api_key_masked"] == "****7890"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_whatsapp_config(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/api/v1/settings/whatsapp",
        json={"phone_number_id": "12345", "access_token": "EAABx...long_token"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["whatsapp_phone_number_id"] == "12345"
    assert body["whatsapp_access_token_masked"] == "****oken"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_telegram_config(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/api/v1/settings/telegram",
        json={"bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["telegram_bot_token_masked"] == "****ew11"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_bot_config(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/api/v1/settings/bot",
        json={"name": "FD Bot", "welcome_message": "Ahlan!", "language": "ar"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["bot_name"] == "FD Bot"
    assert body["bot_welcome_message"] == "Ahlan!"
    assert body["bot_language"] == "ar"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_embedding_config(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.put(
        "/api/v1/settings/embedding",
        json={"model": "text-embedding-3-small"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["embedding_model"] == "text-embedding-3-small"
    assert "embedding_dimensions" not in body
