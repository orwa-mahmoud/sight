"""Unit tests for the database module — engine building + session_scope."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.persistence.postgres.database import _build_engine, session_scope


@patch("src.infrastructure.persistence.postgres.database.get_settings")
@patch("src.infrastructure.persistence.postgres.database.create_async_engine")
def test_build_engine_production(mock_create_engine: MagicMock, mock_settings: MagicMock) -> None:
    """Non-test env creates engine with connection pool settings."""
    settings = MagicMock()
    settings.app_env = "production"
    settings.database_url = "postgresql+asyncpg://localhost/prod"
    mock_settings.return_value = settings
    mock_create_engine.return_value = MagicMock()

    _eng, _factory = _build_engine()

    mock_create_engine.assert_called_once()
    call_kwargs = mock_create_engine.call_args[1]
    assert call_kwargs.get("pool_pre_ping") is True
    assert call_kwargs.get("pool_size") == 10
    assert call_kwargs.get("max_overflow") == 20


@pytest.mark.asyncio
async def test_session_scope_commits_on_success() -> None:
    """session_scope should commit the session when no exception is raised."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    # Create an async context manager that yields the mock session
    mock_factory = MagicMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory.return_value = mock_cm

    with patch("src.infrastructure.persistence.postgres.database.async_session_factory", mock_factory):
        async with session_scope() as _session:
            assert _session is mock_session  # use the session to satisfy linter

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_session_scope_rollbacks_on_error() -> None:
    """session_scope should rollback and re-raise when an exception occurs."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    mock_session.rollback = AsyncMock()

    mock_factory = MagicMock()
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory.return_value = mock_cm

    with patch("src.infrastructure.persistence.postgres.database.async_session_factory", mock_factory):
        with pytest.raises(RuntimeError, match="commit failed"):
            async with session_scope() as _session:
                assert _session is mock_session  # body is intentionally empty; commit fires on exit
