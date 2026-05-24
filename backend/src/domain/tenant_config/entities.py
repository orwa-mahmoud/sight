"""TenantConfig aggregate — per-tenant LLM + channel credentials.

Stores everything the gateway needs to build an LLM client and send
replies through the right channel. API keys are stored as-is in v1;
production should encrypt at rest (PropertyBot uses Fernet — add in v2).

One TenantConfig per Tenant. Created atomically during registration
with safe defaults; the owner updates via the settings API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.shared.entities import BaseEntity
from src.domain.tenant_config.value_objects import LLMProvider


@dataclass(eq=False, kw_only=True)
class TenantConfig(BaseEntity):
    tenant_id: UUID

    # ── LLM ────────────────────────────────────────────────────────
    llm_provider: LLMProvider
    llm_model: str
    llm_api_key: str  # encrypt at rest in production
    llm_max_tokens: int
    llm_temperature: float

    # ── Embedding (RAG ingestion + retrieval) ──────────────────────
    embedding_provider: str
    embedding_model: str
    embedding_api_key: str
    embedding_dimensions: int

    # ── WhatsApp Cloud API ─────────────────────────────────────────
    whatsapp_phone_number_id: str | None
    whatsapp_access_token: str | None
    whatsapp_verify_token: str | None

    # ── Telegram Bot API ───────────────────────────────────────────
    telegram_bot_token: str | None
    telegram_webhook_secret: str | None

    # ── Bot personality ────────────────────────────────────────────
    bot_name: str
    bot_welcome_message: str
    bot_language: str

    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_default(cls, *, tenant_id: UUID) -> TenantConfig:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            llm_provider=LLMProvider.OPENAI,
            llm_model="gpt-4o-mini",
            llm_api_key="",
            llm_max_tokens=1024,
            llm_temperature=0.3,
            embedding_provider="openai",
            embedding_model="text-embedding-3-large",
            embedding_api_key="",
            embedding_dimensions=1536,
            whatsapp_phone_number_id=None,
            whatsapp_access_token=None,
            whatsapp_verify_token=None,
            telegram_bot_token=None,
            telegram_webhook_secret=None,
            bot_name="Front Desk Assistant",
            bot_welcome_message="Hello! How can I help you today?",
            bot_language="en",
            created_at=now,
            updated_at=now,
        )
        # _is_new is set by the caller (register use case)

    def update_llm(
        self,
        *,
        provider: LLMProvider | None = None,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        if provider is not None:
            self.llm_provider = provider
        if model is not None:
            self.llm_model = model
        if api_key is not None:
            self.llm_api_key = api_key
        if max_tokens is not None:
            self.llm_max_tokens = max_tokens
        if temperature is not None:
            self.llm_temperature = temperature
        self.updated_at = datetime.now(UTC)

    def update_embedding(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        if provider is not None:
            self.embedding_provider = provider
        if model is not None:
            self.embedding_model = model
        if api_key is not None:
            self.embedding_api_key = api_key
        if dimensions is not None:
            self.embedding_dimensions = dimensions
        self.updated_at = datetime.now(UTC)

    def update_whatsapp(
        self,
        *,
        phone_number_id: str | None = None,
        access_token: str | None = None,
        verify_token: str | None = None,
    ) -> None:
        if phone_number_id is not None:
            self.whatsapp_phone_number_id = phone_number_id
        if access_token is not None:
            self.whatsapp_access_token = access_token
        if verify_token is not None:
            self.whatsapp_verify_token = verify_token
        self.updated_at = datetime.now(UTC)

    def update_telegram(
        self,
        *,
        bot_token: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        if bot_token is not None:
            self.telegram_bot_token = bot_token
        if webhook_secret is not None:
            self.telegram_webhook_secret = webhook_secret
        self.updated_at = datetime.now(UTC)

    def update_bot(
        self,
        *,
        name: str | None = None,
        welcome_message: str | None = None,
        language: str | None = None,
    ) -> None:
        if name is not None:
            self.bot_name = name.strip()
        if welcome_message is not None:
            self.bot_welcome_message = welcome_message.strip()
        if language is not None:
            self.bot_language = language.strip().lower()
        self.updated_at = datetime.now(UTC)

    @staticmethod
    def mask_key(key: str | None) -> str:
        """Show only last 4 chars — for API responses."""
        if not key or len(key) < 8:
            return "****" if key else ""
        return f"****{key[-4:]}"
