"""End-to-end RAG smoke test (opt-in, requires live LLM + embedding keys).

The rest of the suite exercises the RAG pipeline with mocked ports. This test
drives the *real* path — configure tenant creds → upload a document → wait for
ingestion → ask a question → get a grounded answer — against live provider APIs.

It is SKIPPED unless the required env vars are set, so it never runs in CI by
default (it costs money and depends on third-party availability):

    RUN_E2E_RAG=1 \
    E2E_LLM_API_KEY=sk-... \
    E2E_EMBEDDING_API_KEY=sk-... \
    uv run pytest tests/integration/test_e2e_rag.py -q

Optional overrides: E2E_LLM_PROVIDER (default "openai"), E2E_LLM_MODEL
(default "gpt-4o-mini"), E2E_EMBEDDING_PROVIDER (default "openai"),
E2E_EMBEDDING_MODEL (default "text-embedding-3-small").
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from httpx import AsyncClient

_REQUIRED = ("RUN_E2E_RAG", "E2E_LLM_API_KEY", "E2E_EMBEDDING_API_KEY")
pytestmark = pytest.mark.skipif(
    not all(os.environ.get(k) for k in _REQUIRED),
    reason="e2e RAG test requires RUN_E2E_RAG + live LLM/embedding API keys",
)

_DOC = (
    b"Frontdesk support hours are Monday to Friday, 9am to 5pm Gulf Standard Time. "
    b"The office is closed on public holidays. For urgent issues outside these "
    b"hours, email urgent@frontdesk.example."
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient) -> str:
    slug = f"e2e-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{slug}@e2e.local",
            "password": "supersecure123",
            "full_name": "E2E",
            "tenant_name": f"E2E {slug}",
            "tenant_slug": slug,
        },
    )
    assert resp.status_code == 201, resp.text
    token: str = resp.json()["access_token"]
    return token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_answers_from_uploaded_document(client: AsyncClient) -> None:
    token = await _register(client)
    headers = _auth(token)

    # Configure live provider credentials for this tenant.
    llm = await client.put(
        "/api/v1/settings/llm",
        headers=headers,
        json={
            "provider": os.environ.get("E2E_LLM_PROVIDER", "openai"),
            "model": os.environ.get("E2E_LLM_MODEL", "gpt-4o-mini"),
            "api_key": os.environ["E2E_LLM_API_KEY"],
        },
    )
    assert llm.status_code == 200, llm.text
    emb = await client.put(
        "/api/v1/settings/embedding",
        headers=headers,
        json={
            "provider": os.environ.get("E2E_EMBEDDING_PROVIDER", "openai"),
            "model": os.environ.get("E2E_EMBEDDING_MODEL", "text-embedding-3-small"),
            "api_key": os.environ["E2E_EMBEDDING_API_KEY"],
        },
    )
    assert emb.status_code == 200, emb.text

    # Upload a knowledge-base document.
    upload = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("hours.txt", _DOC, "text/plain")},
    )
    assert upload.status_code in {200, 201}, upload.text
    doc_id = upload.json()["id"]

    # Wait for ingestion to reach "ready" (parse → chunk → embed → persist).
    for _ in range(30):
        listing = await client.get("/api/v1/documents", headers=headers)
        doc = next((d for d in listing.json() if d["id"] == doc_id), None)
        assert doc is not None
        if doc["status"] == "ready":
            break
        assert doc["status"] != "failed", f"ingestion failed: {doc.get('error')}"
        await asyncio.sleep(2)
    else:
        pytest.fail("document did not reach 'ready' in time")

    # Ask a question answerable only from the document.
    chat = await client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "What are your support hours?"},
    )
    assert chat.status_code == 200, chat.text
    answer = chat.json()["response"].lower()
    # The grounded answer should mention the hours from the document.
    assert "9" in answer or "5" in answer or "monday" in answer
