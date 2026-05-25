"""Unit tests for GetUserById use case — error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.auth.use_cases.get_user_by_id import GetUserByIdUseCase
from src.domain.shared.exceptions import AuthenticationError, EntityNotFoundError


def _make_uow(
    *,
    user=None,
    links: list | None = None,
    tenant=None,
) -> MagicMock:
    uow = MagicMock()
    uow.users = MagicMock()
    uow.users.get_by_id = AsyncMock(return_value=user)
    uow.user_tenants = MagicMock()
    uow.user_tenants.list_for_user = AsyncMock(return_value=links or [])
    uow.tenants = MagicMock()
    uow.tenants.get_by_id = AsyncMock(return_value=tenant)
    return uow


def _make_user(*, is_active: bool = True):
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.is_active = is_active
    return user


def _make_link(*, tenant_id=None):
    link = MagicMock()
    link.tenant_id = tenant_id or uuid4()
    link.role = MagicMock()
    link.role.value = "owner"
    return link


def _make_tenant(*, tid=None):
    t = MagicMock()
    t.id = tid or uuid4()
    t.slug = "test-tenant"
    t.name = "Test Tenant"
    return t


@pytest.mark.asyncio
async def test_user_not_found() -> None:
    uow = _make_uow(user=None)
    uc = GetUserByIdUseCase(uow=uow)
    with pytest.raises(EntityNotFoundError, match="User not found"):
        await uc.execute(uuid4())


@pytest.mark.asyncio
async def test_user_inactive() -> None:
    user = _make_user(is_active=False)
    uow = _make_uow(user=user)
    uc = GetUserByIdUseCase(uow=uow)
    with pytest.raises(AuthenticationError, match="disabled"):
        await uc.execute(user.id)


@pytest.mark.asyncio
async def test_user_no_tenant_link() -> None:
    user = _make_user()
    uow = _make_uow(user=user, links=[])
    uc = GetUserByIdUseCase(uow=uow)
    with pytest.raises(AuthenticationError, match="not associated"):
        await uc.execute(user.id)


@pytest.mark.asyncio
async def test_tenant_not_found() -> None:
    user = _make_user()
    link = _make_link()
    uow = _make_uow(user=user, links=[link], tenant=None)
    uc = GetUserByIdUseCase(uow=uow)
    with pytest.raises(EntityNotFoundError, match="Tenant not found"):
        await uc.execute(user.id)


@pytest.mark.asyncio
async def test_happy_path() -> None:
    user = _make_user()
    tid = uuid4()
    link = _make_link(tenant_id=tid)
    tenant = _make_tenant(tid=tid)
    uow = _make_uow(user=user, links=[link], tenant=tenant)
    uc = GetUserByIdUseCase(uow=uow)
    dto = await uc.execute(user.id)
    assert dto.id == user.id
    assert dto.tenant_id == tid
    assert dto.role == "owner"
