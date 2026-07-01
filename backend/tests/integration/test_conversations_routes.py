"""Integration tests for conversations routes — covers list, daily-summary,
and get-messages endpoints with seeded data."""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.entities import Conversation, Message
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.infrastructure.persistence.postgres.database import async_session_factory
from tests.conftest import register_and_token


async def _seed_conversation_with_messages(
    tenant_id: UUID,
) -> tuple[UUID, str]:
    """Create a conversation with two visible messages and return (conv_id, thread_id)."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = Conversation.start(
            tenant_id=tenant_id,
            thread_id=f"thread-test-{tenant_id.hex[:8]}",
            channel=ConversationChannel.WEB,
        )
        conv.touch()
        await uow.conversations.save(conv)
        await uow.flush()

        msg1 = Message.create(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role=ConversationRole.USER,
            content="Hello, what are your hours?",
        )
        await uow.messages.save(msg1)

        msg2 = Message.create(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role=ConversationRole.ASSISTANT,
            content="We are open 9-5 Sunday through Thursday.",
        )
        await uow.messages.save(msg2)

        # A hidden message that should NOT appear in get_messages
        hidden = Message.create(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            role=ConversationRole.SYSTEM,
            content="(internal system note)",
            hidden=True,
        )
        await uow.messages.save(hidden)

        await uow.commit()
        return conv.id, conv.thread_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_conversations_with_data(client: AsyncClient) -> None:
    token, _, tenant_id = await register_and_token(client)
    await _seed_conversation_with_messages(UUID(tenant_id))

    resp = await client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    conv = body[0]
    assert "id" in conv
    assert "thread_id" in conv
    assert conv["channel"] == "web"
    assert conv["last_message_at"] is not None
    assert "created_at" in conv


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_conversations_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daily_summary_with_data(client: AsyncClient) -> None:
    token, _, tenant_id = await register_and_token(client)
    await _seed_conversation_with_messages(UUID(tenant_id))

    resp = await client.get(
        "/api/v1/conversations/daily-summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] >= 2
    assert body["active_conversations"] >= 1
    assert "date" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_for_conversation(client: AsyncClient) -> None:
    token, _, tenant_id = await register_and_token(client)
    conv_id, _ = await _seed_conversation_with_messages(UUID(tenant_id))

    resp = await client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    messages = resp.json()
    # Only visible messages (hidden=False) are returned
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello, what are your hours?"
    assert messages[1]["role"] == "assistant"
    assert "id" in messages[0]
    assert "created_at" in messages[0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_respects_limit(client: AsyncClient) -> None:
    token, _, tenant_id = await register_and_token(client)
    conv_id, _ = await _seed_conversation_with_messages(UUID(tenant_id))

    resp = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) == 1  # capped (the conversation has 2 visible messages)

    # Out-of-range limits are rejected by validation.
    too_big = await client.get(
        f"/api/v1/conversations/{conv_id}/messages?limit=9999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert too_big.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_not_found(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(
        f"/api/v1/conversations/{fake_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_cross_tenant_denied(client: AsyncClient) -> None:
    """A user should not see messages from another tenant's conversation."""
    # Tenant A seeds a conversation
    _token_a, _, tenant_a = await register_and_token(client)
    conv_id, _ = await _seed_conversation_with_messages(UUID(tenant_a))

    # Tenant B registers separately
    token_b, _, _ = await register_and_token(client)

    resp = await client.get(
        f"/api/v1/conversations/{conv_id}/messages",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_messages_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000/messages")
    assert resp.status_code == 401
