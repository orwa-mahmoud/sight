"""Integration tests for the questions routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


async def _submit_question(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/api/v1/questions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "channel": "web",
            "question_text": "What are your hours?",
            "asker_name": "Sara",
            "asker_contact": "sara@test.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_submit_question(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    q = await _submit_question(client, token)
    assert q["status"] == "submitted"
    assert q["question_text"] == "What are your hours?"
    assert q["asker_name"] == "Sara"


@pytest.mark.asyncio
async def test_list_questions(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    await _submit_question(client, token)
    resp = await client.get("/api/v1/questions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_list_questions_with_status_filter(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    await _submit_question(client, token)
    resp = await client.get(
        "/api/v1/questions?status=submitted",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    for q in resp.json():
        assert q["status"] == "submitted"


@pytest.mark.asyncio
async def test_get_question(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    q = await _submit_question(client, token)
    resp = await client.get(
        f"/api/v1/questions/{q['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == q["id"]


@pytest.mark.asyncio
async def test_reply_to_question(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    q = await _submit_question(client, token)
    resp = await client.post(
        f"/api/v1/questions/{q['id']}/reply",
        headers={"Authorization": f"Bearer {token}"},
        json={"reply": "We are open 9-5."},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["owner_reply"] == "We are open 9-5."


@pytest.mark.asyncio
async def test_close_question(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    q = await _submit_question(client, token)
    resp = await client.post(
        f"/api/v1/questions/{q['id']}/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_questions_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/questions")
    assert resp.status_code == 401
