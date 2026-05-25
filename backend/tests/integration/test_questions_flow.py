"""Integration tests for the escalation flow: submit → list → reply → close."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_OWNER = {
    "email": "owner@example.com",
    "password": "supersecure123",
    "full_name": "Owner",
    "tenant_name": "Test",
    "tenant_slug": "test",
}


async def _register_and_token(client: AsyncClient) -> str:
    resp = await client.post("/api/v1/auth/register", json=_OWNER)
    assert resp.status_code == 201
    return resp.json()["access_token"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_submit_then_list_then_reply(client: AsyncClient) -> None:
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # ── Submit ────────────────────────────────────────────────────
    resp = await client.post(
        "/api/v1/questions",
        json={
            "channel": "whatsapp",
            "question_text": "Are you open on Saturdays?",
            "ai_answer_attempt": "I'm not sure about weekend hours.",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    submitted = resp.json()
    assert submitted["status"] == "submitted"
    question_id = submitted["id"]

    # ── List ──────────────────────────────────────────────────────
    resp = await client.get("/api/v1/questions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # ── Filter by status=submitted ────────────────────────────────
    resp = await client.get("/api/v1/questions?status=submitted", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # ── Reply ─────────────────────────────────────────────────────
    resp = await client.post(
        f"/api/v1/questions/{question_id}/reply",
        json={"reply": "Yes, 10am-2pm on Saturdays."},
        headers=headers,
    )
    assert resp.status_code == 200
    resolved = resp.json()
    assert resolved["status"] == "resolved"
    assert resolved["owner_reply"] == "Yes, 10am-2pm on Saturdays."
    assert resolved["replied_at"] is not None

    # ── Replying twice fails ──────────────────────────────────────
    resp = await client.post(
        f"/api/v1/questions/{question_id}/reply",
        json={"reply": "different answer"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_close_without_reply(client: AsyncClient) -> None:
    token = await _register_and_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/questions",
        json={"channel": "telegram", "question_text": "Spam question"},
        headers=headers,
    )
    question_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/questions/{question_id}/close", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cross_tenant_access_forbidden(client: AsyncClient) -> None:
    # Tenant A creates a question.
    token_a = await _register_and_token(client)
    resp = await client.post(
        "/api/v1/questions",
        json={"channel": "web", "question_text": "From tenant A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    question_id = resp.json()["id"]

    # Tenant B registers separately.
    resp = await client.post(
        "/api/v1/auth/register",
        json={**_OWNER, "email": "other@example.com", "tenant_slug": "other"},
    )
    token_b = resp.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B sees no questions.
    resp = await client.get("/api/v1/questions", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []

    # Tenant B can't fetch tenant A's question.
    resp = await client.get(f"/api/v1/questions/{question_id}", headers=headers_b)
    assert resp.status_code in {403, 404}
