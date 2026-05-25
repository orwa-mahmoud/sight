"""Integration tests for LLM usage stats route — covers the tenant resolution
path and response shape."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_usage_stats_returns_zeroes_for_new_tenant(client: AsyncClient) -> None:
    """A freshly registered tenant has zero usage across all fields."""
    token, _, _ = await register_and_token(client)

    resp = await client.get(
        "/api/v1/llm-usage/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_calls"] == 0
    assert body["total_input_tokens"] == 0
    assert body["total_output_tokens"] == 0
    assert body["total_cache_read_tokens"] == 0
    assert body["total_cost"] == "0"
    assert body["total_input_cost"] == "0"
    assert body["total_output_cost"] == "0"
    assert body["total_cache_read_cost"] == "0"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_usage_stats_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/llm-usage/stats")
    assert resp.status_code == 401
