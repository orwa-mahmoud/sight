"""Settings API schemas — masked responses, partial updates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.tenant_config.value_objects import LLMProvider


class TenantConfigResponse(BaseModel):
    """Returned to the owner — secrets are masked (last 4 chars)."""

    # LLM
    llm_provider: str
    llm_model: str
    llm_api_key_masked: str
    llm_max_tokens: int
    llm_temperature: float
    # Embedding
    embedding_provider: str
    embedding_model: str
    embedding_api_key_masked: str
    embedding_dimensions: int
    # WhatsApp
    whatsapp_phone_number_id: str | None
    whatsapp_access_token_masked: str | None
    whatsapp_verify_token_masked: str | None
    # Telegram
    telegram_bot_token_masked: str | None
    telegram_webhook_secret_masked: str | None
    # Bot
    bot_name: str
    bot_welcome_message: str
    bot_language: str


class UpdateLLMConfig(BaseModel):
    provider: LLMProvider | None = None
    model: str | None = Field(default=None, max_length=64)
    api_key: str | None = Field(default=None, max_length=512)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class UpdateEmbeddingConfig(BaseModel):
    provider: str | None = Field(default=None, max_length=32)
    model: str | None = Field(default=None, max_length=64)
    api_key: str | None = Field(default=None, max_length=512)
    dimensions: int | None = Field(default=None, ge=256, le=4096)


class UpdateWhatsAppConfig(BaseModel):
    phone_number_id: str | None = Field(default=None, max_length=64)
    access_token: str | None = Field(default=None, max_length=512)
    verify_token: str | None = Field(default=None, max_length=255)


class UpdateTelegramConfig(BaseModel):
    bot_token: str | None = Field(default=None, max_length=512)
    webhook_secret: str | None = Field(default=None, max_length=255)


class UpdateBotConfig(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    welcome_message: str | None = Field(default=None, max_length=2000)
    language: str | None = Field(default=None, max_length=8)
