"""Unit tests for the /chat endpoint handler logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.types import ChatResult
from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.webhooks.chat_api import ChatRequest, chat


def _make_user(*, user_id=None, email="test@t.com", full_name="Test"):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = email
    user.full_name = full_name
    return user


def _make_uow(*, links=None):
    uow = MagicMock()
    uow.user_tenants = MagicMock()
    uow.user_tenants.list_for_user = AsyncMock(return_value=links or [])
    return uow


def _make_link(*, tenant_id=None):
    link = MagicMock()
    link.tenant_id = tenant_id or uuid4()
    return link


@pytest.mark.asyncio
async def test_chat_no_tenant_link_raises() -> None:
    user = _make_user()
    uow = _make_uow(links=[])
    req = ChatRequest(message="hi")

    with pytest.raises(AuthenticationError, match="not associated"):
        await chat(req, current_user=user, uow=uow)


@pytest.mark.asyncio
async def test_chat_happy_path() -> None:
    tid = uuid4()
    user = _make_user()
    link = _make_link(tenant_id=tid)
    uow = _make_uow(links=[link])
    req = ChatRequest(message="hello there")

    mock_result = ChatResult(response="Hi!", thread_id="t-1", escalated=False, request_id="r-1")

    with patch("src.drivers.api.webhooks.chat_api.chat_with_agent", new_callable=AsyncMock, return_value=mock_result):
        resp = await chat(req, current_user=user, uow=uow)

    assert resp.response == "Hi!"
    assert resp.thread_id == "t-1"
    assert resp.escalated is False
    assert resp.request_id == "r-1"


@pytest.mark.asyncio
async def test_chat_escalated_result() -> None:
    tid = uuid4()
    user = _make_user()
    link = _make_link(tenant_id=tid)
    uow = _make_uow(links=[link])
    req = ChatRequest(message="I want a refund")

    mock_result = ChatResult(response="Let me connect you.", thread_id="t-2", escalated=True, request_id="r-2")

    with patch("src.drivers.api.webhooks.chat_api.chat_with_agent", new_callable=AsyncMock, return_value=mock_result):
        resp = await chat(req, current_user=user, uow=uow)

    assert resp.escalated is True
