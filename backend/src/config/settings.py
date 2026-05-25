"""Application settings — loaded from environment via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ────────────────────────────────────────────────
    app_name: str = "frontdesk"
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Database ───────────────────────────────────────────────────
    database_url: str
    database_url_sync: str
    database_url_test: str | None = None

    # ── Redis ──────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Auth (JWT) ─────────────────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ── Encryption (Fernet key for tenant secrets at rest) ─────────
    encryption_key: str | None = None

    # ── Observability ──────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "frontdesk-backend"
    sentry_dsn: str | None = None

    # ── CORS ───────────────────────────────────────────────────────
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Resolve settings once per process. Cached so DI containers reuse the same instance."""
    return Settings()
