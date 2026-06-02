"""Integration: domain error messages are localized via Accept-Language."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_BAD_LOGIN = {"email": "nobody@example.com", "password": "wrong-password"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_detail_english_by_default(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/login", json=_BAD_LOGIN)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_detail_localized_to_arabic(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json=_BAD_LOGIN,
        headers={"Accept-Language": "ar"},
    )
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail != "Invalid email or password"
    assert detail.strip()  # non-empty Arabic translation
