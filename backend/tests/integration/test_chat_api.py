"""Integration tests for the /chat test endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from src.ai.types import ChatResult, ChatSource
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_returns_sources_and_tokens(client: AsyncClient) -> None:
    """The /chat response surfaces RAG sources + token usage for the dashboard test view.

    Exercises the real auth + tenant-resolution path and the ChatResult →
    ChatResponse serialization; the agent run itself is stubbed.
    """
    token, _, tenant_id = await register_and_token(client)
    mock_result = ChatResult(
        response="We are open 9-5.",
        thread_id=f"api:owner:{tenant_id}",
        escalated=False,
        request_id="req-1",
        sources=[ChatSource(document_id="doc-1", snippet="We are open 9 to 5 daily.", score=0.87)],
        input_tokens=210,
        output_tokens=18,
    )
    with patch(
        "src.drivers.api.webhooks.chat_api.chat_with_agent",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post(
            "/api/v1/chat",
            json={"message": "what are your hours?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "We are open 9-5."
    assert body["input_tokens"] == 210
    assert body["output_tokens"] == 18
    assert body["sources"] == [{"document_id": "doc-1", "snippet": "We are open 9 to 5 daily.", "score": 0.87}]
