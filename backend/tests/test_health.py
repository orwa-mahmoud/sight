"""Smoke tests for the health + readiness endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Response
from httpx import AsyncClient

from src.drivers.api.v1.health import routes


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "sight"


@pytest.mark.asyncio
async def test_readiness_ok_when_dependencies_up(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_down() -> None:
    response = Response()
    with (
        patch.object(routes, "_check_database", AsyncMock(return_value=False)),
        patch.object(routes, "_check_redis", AsyncMock(return_value=True)),
    ):
        body = await routes.readiness(response)
    # DB is required → not ready → 503 so the orchestrator stops routing here.
    assert response.status_code == 503
    assert body.database == "error"
    assert body.redis == "ok"
