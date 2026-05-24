"""Unit tests for the domain error → HTTP response handler."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.shared.exceptions import AuthenticationError, EntityNotFoundError
from src.drivers.api.responses import domain_error_handler


@pytest.mark.asyncio
async def test_maps_not_found_to_404() -> None:
    exc = EntityNotFoundError("User not found")
    resp = await domain_error_handler(MagicMock(), exc)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_maps_auth_error_to_401() -> None:
    exc = AuthenticationError("Bad token")
    resp = await domain_error_handler(MagicMock(), exc)
    assert resp.status_code == 401
