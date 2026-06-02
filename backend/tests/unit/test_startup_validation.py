"""Unit tests for production-settings validation."""

from __future__ import annotations

import pytest

from src.bootstrap.startup import validate_production_settings
from src.config.settings import Settings


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "database_url_sync": "postgresql://u:p@localhost/db",
        "jwt_secret_key": "x",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_production_without_encryption_key_raises() -> None:
    with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
        validate_production_settings(_settings(app_env="production", encryption_key=None))


def test_production_with_encryption_key_passes() -> None:
    validate_production_settings(_settings(app_env="production", encryption_key="a-key"))


def test_non_production_without_key_passes() -> None:
    validate_production_settings(_settings(app_env="development", encryption_key=None))
