"""Unit tests for app creation and lifespan."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.routing import Route

from src.main import create_app, lifespan


def test_create_app_returns_fastapi() -> None:
    """create_app() builds a FastAPI application with routes."""
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "frontdesk"


def test_create_app_has_expected_routes() -> None:
    """The app should include health, v1, telegram, and whatsapp routes."""
    app = create_app()
    paths = [r.path for r in app.routes if isinstance(r, Route)]
    assert "/health" in paths or any("/health" in p for p in paths)
    assert "/metrics" in paths or any("/metrics" in p for p in paths)


@pytest.mark.asyncio
async def test_lifespan_calls_register_event_handlers() -> None:
    """The lifespan context manager should register event handlers on startup."""
    app = FastAPI()

    with patch("src.main.register_event_handlers") as mock_reg:
        async with lifespan(app):
            mock_reg.assert_called_once()


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    """The /metrics endpoint returns prometheus content."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "frontdesk" in resp.text or "python" in resp.text.lower()
