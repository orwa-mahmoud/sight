"""Unit tests for request ID middleware."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.drivers.api.middleware.request_id import _metric_path
from src.main import app


def test_metric_path_uses_route_template() -> None:
    req = MagicMock()
    req.scope = {"route": MagicMock(path="/api/v1/documents/{document_id}")}
    assert _metric_path(req) == "/api/v1/documents/{document_id}"


def test_metric_path_unmatched_when_no_route() -> None:
    req = MagicMock()
    req.scope = {}
    assert _metric_path(req) == "unmatched"


@pytest.mark.asyncio
async def test_unmatched_path_does_not_leak_into_metrics() -> None:
    # A 404 / scanner URL must not become its own Prometheus series.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/this-path-does-not-exist-zzz")
        metrics = (await client.get("/metrics")).text
    assert "this-path-does-not-exist-zzz" not in metrics


@pytest.mark.asyncio
async def test_response_has_request_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert "x-request-id" in resp.headers


@pytest.mark.asyncio
async def test_custom_request_id_echoed() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Request-ID": "custom-123"})
    assert resp.headers.get("x-request-id") == "custom-123"
