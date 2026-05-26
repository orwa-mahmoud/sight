"""Unit tests for FastAPI dependencies — error paths in get_current_user."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_missing_token() -> None:
    uow = MagicMock()
    with pytest.raises(AuthenticationError, match="Missing authentication"):
        await get_current_user(request=MagicMock(cookies={}), token=None, uow=uow)


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_claim() -> None:
    uow = MagicMock()
    mock_jwt = MagicMock()
    mock_jwt.decode.return_value = {"exp": 999}  # no "sub"

    with patch("src.drivers.api.dependencies.get_jwt_service", return_value=mock_jwt):
        with pytest.raises(AuthenticationError, match="Token missing subject"):
            await get_current_user(request=MagicMock(cookies={}), token="some.jwt.token", uow=uow)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found() -> None:
    uid = uuid4()
    uow = MagicMock()
    uow.users = MagicMock()
    uow.users.get_by_id = AsyncMock(return_value=None)

    mock_jwt = MagicMock()
    mock_jwt.decode.return_value = {"sub": str(uid)}

    with patch("src.drivers.api.dependencies.get_jwt_service", return_value=mock_jwt):
        with pytest.raises(AuthenticationError, match="no longer exists"):
            await get_current_user(request=MagicMock(cookies={}), token="tok", uow=uow)


@pytest.mark.asyncio
async def test_get_current_user_inactive_user() -> None:
    uid = uuid4()
    user = MagicMock()
    user.is_active = False

    uow = MagicMock()
    uow.users = MagicMock()
    uow.users.get_by_id = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_jwt.decode.return_value = {"sub": str(uid)}

    with patch("src.drivers.api.dependencies.get_jwt_service", return_value=mock_jwt):
        with pytest.raises(AuthenticationError, match="no longer exists"):
            await get_current_user(request=MagicMock(cookies={}), token="tok", uow=uow)


@pytest.mark.asyncio
async def test_get_current_user_happy_path() -> None:
    uid = uuid4()
    user = MagicMock()
    user.is_active = True

    uow = MagicMock()
    uow.users = MagicMock()
    uow.users.get_by_id = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_jwt.decode.return_value = {"sub": str(uid)}

    with patch("src.drivers.api.dependencies.get_jwt_service", return_value=mock_jwt):
        result = await get_current_user(request=MagicMock(cookies={}), token="tok", uow=uow)
    assert result is user
