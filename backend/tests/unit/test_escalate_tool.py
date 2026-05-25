"""Tests for the escalate_question tool runner."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.ai.tools.escalate_question import run_escalate_question
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.infrastructure.persistence.postgres.database import async_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_escalate_creates_question(client: None) -> None:
    from src.domain.tenants.entities import Tenant  # noqa: PLC0415

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="Esc", slug=f"esc-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await run_escalate_question(
            arguments={"question_text": "What's the return policy?", "ai_answer_attempt": "I'm not sure."},
            tenant_id=t.id,
            channel=ConversationChannel.WHATSAPP,
            conversation_id=None,
            asker_name="Sara",
            asker_contact="+971500000000",
            uow=uow,
        )
        await uow.commit()

    assert result["status"] == "escalated"
    assert "question_id" in result
