"""Unit tests for CloseQuestion use case — error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.questions.commands import CloseQuestion
from src.application.questions.use_cases.close_question import CloseQuestionUseCase
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.questions.entities import Question
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


def _make_question(*, tenant_id=None) -> Question:
    return Question.submit(
        tenant_id=tenant_id or uuid4(),
        channel=ConversationChannel.API,
        question_text="What is your policy?",
    )


@pytest.mark.asyncio
async def test_close_question_not_found() -> None:
    uow = MagicMock()
    uow.questions = MagicMock()
    uow.questions.get_by_id = AsyncMock(return_value=None)

    uc = CloseQuestionUseCase(uow=uow)
    cmd = CloseQuestion(tenant_id=uuid4(), question_id=uuid4())
    with pytest.raises(EntityNotFoundError, match="Question not found"):
        await uc.execute(cmd)


@pytest.mark.asyncio
async def test_close_question_wrong_tenant() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    question = _make_question(tenant_id=tenant_a)

    uow = MagicMock()
    uow.questions = MagicMock()
    uow.questions.get_by_id = AsyncMock(return_value=question)

    uc = CloseQuestionUseCase(uow=uow)
    cmd = CloseQuestion(tenant_id=tenant_b, question_id=question.id)
    with pytest.raises(AuthorizationError, match="does not belong"):
        await uc.execute(cmd)


@pytest.mark.asyncio
async def test_close_question_happy_path() -> None:
    tid = uuid4()
    question = _make_question(tenant_id=tid)

    uow = MagicMock()
    uow.questions = MagicMock()
    uow.questions.get_by_id = AsyncMock(return_value=question)
    uow.questions.save = AsyncMock()

    uc = CloseQuestionUseCase(uow=uow)
    cmd = CloseQuestion(tenant_id=tid, question_id=question.id)
    dto = await uc.execute(cmd)
    assert dto.status == "closed"
