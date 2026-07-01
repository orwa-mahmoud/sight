"""Unit tests for SubmitQuestion — tenant ownership of client-supplied foreign keys."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.application.questions.commands import SubmitQuestion
from src.application.questions.use_cases.submit_question import SubmitQuestionUseCase
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.shared.exceptions import AuthorizationError


def _cmd(tenant_id: UUID, *, contact_id: UUID | None = None, conversation_id: UUID | None = None) -> SubmitQuestion:
    return SubmitQuestion(
        tenant_id=tenant_id,
        channel=ConversationChannel.API,
        question_text="What is my balance?",
        conversation_id=conversation_id,
        contact_id=contact_id,
        ai_answer_attempt="I can't access account balances.",
    )


def _uow() -> MagicMock:
    uow = MagicMock()
    uow.contacts.get_by_id = AsyncMock(return_value=None)
    uow.conversations.get_by_id = AsyncMock(return_value=None)
    uow.questions.save = AsyncMock()
    uow.track = MagicMock()
    return uow


@pytest.mark.asyncio
async def test_submit_rejects_foreign_contact() -> None:
    tenant = uuid4()
    uow = _uow()
    foreign = MagicMock()
    foreign.tenant_id = uuid4()  # different tenant
    uow.contacts.get_by_id.return_value = foreign

    with pytest.raises(AuthorizationError):
        await SubmitQuestionUseCase(uow=uow).execute(_cmd(tenant, contact_id=uuid4()))
    uow.questions.save.assert_not_called()


@pytest.mark.asyncio
async def test_submit_rejects_missing_contact() -> None:
    uow = _uow()  # get_by_id returns None
    with pytest.raises(AuthorizationError):
        await SubmitQuestionUseCase(uow=uow).execute(_cmd(uuid4(), contact_id=uuid4()))


@pytest.mark.asyncio
async def test_submit_rejects_foreign_conversation() -> None:
    tenant = uuid4()
    uow = _uow()
    foreign = MagicMock()
    foreign.tenant_id = uuid4()
    uow.conversations.get_by_id.return_value = foreign

    with pytest.raises(AuthorizationError):
        await SubmitQuestionUseCase(uow=uow).execute(_cmd(tenant, conversation_id=uuid4()))


@pytest.mark.asyncio
async def test_submit_accepts_own_contact_and_conversation() -> None:
    tenant = uuid4()
    uow = _uow()
    own_contact = MagicMock()
    own_contact.tenant_id = tenant
    own_conv = MagicMock()
    own_conv.tenant_id = tenant
    uow.contacts.get_by_id.return_value = own_contact
    uow.conversations.get_by_id.return_value = own_conv

    dto = await SubmitQuestionUseCase(uow=uow).execute(_cmd(tenant, contact_id=uuid4(), conversation_id=uuid4()))

    assert dto.tenant_id == tenant
    uow.questions.save.assert_awaited_once()
