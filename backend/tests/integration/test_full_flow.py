"""Full end-to-end integration test — register + settings + questions + conversations."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_owner_full_onboarding_flow(client: AsyncClient) -> None:
    """Owner registers → configures LLM → uploads doc → asks question → checks stats."""
    # 1. Register
    token, _user_id, _tenant_id = await register_and_token(client)
    h = {"Authorization": f"Bearer {token}"}

    # 2. Get settings (default config)
    resp = await client.get("/api/v1/settings", headers=h)
    assert resp.status_code == 200
    assert resp.json()["llm_provider"] == "openai"

    # 3. Update LLM config
    resp = await client.put("/api/v1/settings/llm", json={"model": "gpt-4o"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["llm_model"] == "gpt-4o"

    # 4. Check documents (empty)
    resp = await client.get("/api/v1/documents", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []

    # 5. Check questions (empty)
    resp = await client.get("/api/v1/questions", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []

    # 6. Submit a question
    resp = await client.post(
        "/api/v1/questions",
        json={
            "channel": "whatsapp",
            "question_text": "What are your office hours?",
        },
        headers=h,
    )
    assert resp.status_code == 201
    q_id = resp.json()["id"]

    # 7. Check inbox has 1 question
    resp = await client.get("/api/v1/questions?status=submitted", headers=h)
    assert len(resp.json()) == 1

    # 8. Reply to question
    resp = await client.post(f"/api/v1/questions/{q_id}/reply", json={"reply": "9-5 Sun-Thu"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    # 9. Check usage stats
    resp = await client.get("/api/v1/llm-usage/stats", headers=h)
    assert resp.status_code == 200

    # 10. Check daily summary
    resp = await client.get("/api/v1/conversations/daily-summary", headers=h)
    assert resp.status_code == 200

    # 11. Get tenant info
    resp = await client.get("/api/v1/tenants/me", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    # 12. Refresh token
    resp = await client.post("/api/v1/auth/refresh", headers=h)
    assert resp.status_code == 200
    assert resp.json()["access_token"]


x = 1
