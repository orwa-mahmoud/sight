"""TenantConfig ORM model — per-tenant LLM + channel credentials."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.postgres.models import Base


class TenantConfigModel(Base):
    __tablename__ = "tenant_configs"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_config_tenant"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # LLM
    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    llm_model: Mapped[str] = mapped_column(String(64), nullable=False, default="gpt-4o-mini")
    llm_api_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    llm_max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    llm_temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    # Embedding
    embedding_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, default="text-embedding-3-large")
    embedding_api_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # WhatsApp
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    whatsapp_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_verify_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_app_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Telegram
    telegram_bot_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Bot personality
    bot_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Front Desk Assistant")
    bot_welcome_message: Mapped[str] = mapped_column(Text, nullable=False, default="Hello! How can I help you today?")
    bot_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
