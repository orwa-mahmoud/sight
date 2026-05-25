"""Integration tests for the /chat test endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/chat", json={"message": "hi"})
    assert resp.status_code == 401

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_requires_llm_config(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.post(
        "/api/v1/chat",
        json={"message": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should fail because no LLM API key is configured
    assert resp.status_code == 400
    assert "API key" in resp.json()["detail"] or "configuration" in resp.json()["detail"].lower()
