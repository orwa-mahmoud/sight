"""Durable, DB-level de-duplication of inbound messages by provider_message_id.

A redelivered webhook (at-least-once channels) must not create a second message
or trigger a second agent turn. The partial unique index on
(conversation_id, provider_message_id) enforces this even if Redis is down or two
duplicate deliveries race.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory


def _cmd(tenant_id: UUID, thread_id: str, provider_message_id: str | None) -> SaveThreadMessage:
    return SaveThreadMessage(
        tenant_id=tenant_id,
        thread_id=thread_id,
        channel=ConversationChannel.WHATSAPP,
        role=ConversationRole.USER,
        content="hi",
        provider_message_id=provider_message_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_same_provider_id_is_deduplicated(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="Dedup", slug=f"dedup-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.commit()

    thread_id = f"whatsapp:+100:{tenant.id}"
    cmd = _cmd(tenant.id, thread_id, "wamid.SAME")

    # First delivery → saved.
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        first = await SaveThreadMessageUseCase(uow=uow).execute(cmd)
        await uow.commit()
        assert first.is_duplicate is False

    # Redelivery of the same provider id → skipped.
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        second = await SaveThreadMessageUseCase(uow=uow).execute(cmd)
        await uow.commit()
        assert second.is_duplicate is True

    # Exactly one inbound row persisted.
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = await uow.conversations.get_by_thread_id(thread_id)
        assert conv is not None
        msgs = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        assert [m.provider_message_id for m in msgs].count("wamid.SAME") == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_different_provider_ids_both_saved(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="Dedup2", slug=f"dedup2-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.commit()

    thread_id = f"whatsapp:+200:{tenant.id}"
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        a = await SaveThreadMessageUseCase(uow=uow).execute(_cmd(tenant.id, thread_id, "wamid.A"))
        b = await SaveThreadMessageUseCase(uow=uow).execute(_cmd(tenant.id, thread_id, "wamid.B"))
        await uow.commit()
        assert a.is_duplicate is False
        assert b.is_duplicate is False

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = await uow.conversations.get_by_thread_id(thread_id)
        assert conv is not None
        msgs = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        assert len([m for m in msgs if m.provider_message_id in ("wamid.A", "wamid.B")]) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_null_provider_id_is_never_deduplicated(client: None) -> None:
    """API/dashboard messages have no provider id — they must always be saved."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="Dedup3", slug=f"dedup3-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.commit()

    thread_id = f"api:web:{tenant.id}"
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        r1 = await SaveThreadMessageUseCase(uow=uow).execute(_cmd(tenant.id, thread_id, None))
        r2 = await SaveThreadMessageUseCase(uow=uow).execute(_cmd(tenant.id, thread_id, None))
        await uow.commit()
        assert r1.is_duplicate is False
        assert r2.is_duplicate is False

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = await uow.conversations.get_by_thread_id(thread_id)
        assert conv is not None
        msgs = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        assert len(msgs) == 2
