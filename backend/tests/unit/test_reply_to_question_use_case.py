"""Unit tests for ReplyToQuestion use case — error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.questions.commands import ReplyToQuestion
from src.application.questions.use_cases.reply_to_question import ReplyToQuestionUseCase
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.questions.entities import Question
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


def _make_question(*, tenant_id=None) -> Question:
    return Question.submit(
        tenant_id=tenant_id or uuid4(),
        channel=ConversationChannel.WHATSAPP,
        question_text="How much is a room?",
    )


@pytest.mark.asyncio
async def test_reply_question_not_found() -> None:
    uow = MagicMock()
    uow.questions = MagicMock()
    uow.questions.get_by_id = AsyncMock(return_value=None)

    uc = ReplyToQuestionUseCase(uow=uow)
    cmd = ReplyToQuestion(tenant_id=uuid4(), question_id=uuid4(), replied_by_user_id=uuid4(), reply="Sure")
    with pytest.raises(EntityNotFoundError, match="Question not found"):
        await uc.execute(cmd)


@pytest.mark.asyncio
async def test_reply_question_wrong_tenant() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    question = _make_question(tenant_id=tenant_a)

    uow = MagicMock()
    uow.questions = MagicMock()
    uow.questions.get_by_id = AsyncMock(return_value=question)

    uc = ReplyToQuestionUseCase(uow=uow)
    cmd = ReplyToQuestion(tenant_id=tenant_b, question_id=question.id, replied_by_user_id=uuid4(), reply="Answer")
    with pytest.raises(AuthorizationError, match="does not belong"):
        await uc.execute(cmd)


@pytest.mark.asyncio
async def test_reply_question_happy_path() -> None:
    tid = uuid4()
    question = _make_question(tenant_id=tid)
    user_id = uuid4()

    uow = MagicMock()
    uow.questions = MagicMock()
    uow.questions.get_by_id = AsyncMock(return_value=question)
    uow.questions.save = AsyncMock()

    uc = ReplyToQuestionUseCase(uow=uow)
    cmd = ReplyToQuestion(tenant_id=tid, question_id=question.id, replied_by_user_id=user_id, reply="100 AED per night")
    dto = await uc.execute(cmd)
    assert dto.status == "resolved"
    assert dto.owner_reply == "100 AED per night"
