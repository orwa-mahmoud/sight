"""PostgreSQL TenantConfig repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenant_config.value_objects import LLMProvider
from src.infrastructure.persistence.postgres.models.tenant_config import TenantConfigModel


class PostgresTenantConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, config: TenantConfig) -> None:
        if config.is_new:
            self._session.add(self._to_model(config))
            config.mark_persisted()
            return
        model = await self._session.get(TenantConfigModel, config.id)
        if model is None:
            self._session.add(self._to_model(config))
            return
        model.llm_provider = config.llm_provider.value
        model.llm_model = config.llm_model
        model.llm_api_key = config.llm_api_key
        model.llm_max_tokens = config.llm_max_tokens
        model.llm_temperature = config.llm_temperature
        model.embedding_provider = config.embedding_provider
        model.embedding_model = config.embedding_model
        model.embedding_api_key = config.embedding_api_key
        model.embedding_dimensions = config.embedding_dimensions
        model.whatsapp_phone_number_id = config.whatsapp_phone_number_id
        model.whatsapp_access_token = config.whatsapp_access_token
        model.whatsapp_verify_token = config.whatsapp_verify_token
        model.whatsapp_app_secret = config.whatsapp_app_secret
        model.telegram_bot_token = config.telegram_bot_token
        model.telegram_webhook_secret = config.telegram_webhook_secret
        model.bot_name = config.bot_name
        model.bot_welcome_message = config.bot_welcome_message
        model.bot_language = config.bot_language
        model.updated_at = config.updated_at

    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantConfig | None:
        stmt = select(TenantConfigModel).where(TenantConfigModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_model(c: TenantConfig) -> TenantConfigModel:
        return TenantConfigModel(
            id=c.id,
            tenant_id=c.tenant_id,
            llm_provider=c.llm_provider.value,
            llm_model=c.llm_model,
            llm_api_key=c.llm_api_key,
            llm_max_tokens=c.llm_max_tokens,
            llm_temperature=c.llm_temperature,
            embedding_provider=c.embedding_provider,
            embedding_model=c.embedding_model,
            embedding_api_key=c.embedding_api_key,
            embedding_dimensions=c.embedding_dimensions,
            whatsapp_phone_number_id=c.whatsapp_phone_number_id,
            whatsapp_access_token=c.whatsapp_access_token,
            whatsapp_verify_token=c.whatsapp_verify_token,
            whatsapp_app_secret=c.whatsapp_app_secret,
            telegram_bot_token=c.telegram_bot_token,
            telegram_webhook_secret=c.telegram_webhook_secret,
            bot_name=c.bot_name,
            bot_welcome_message=c.bot_welcome_message,
            bot_language=c.bot_language,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )

    @staticmethod
    def _to_entity(m: TenantConfigModel) -> TenantConfig:
        return TenantConfig(
            id=m.id,
            tenant_id=m.tenant_id,
            llm_provider=LLMProvider(m.llm_provider),
            llm_model=m.llm_model,
            llm_api_key=m.llm_api_key,
            llm_max_tokens=m.llm_max_tokens,
            llm_temperature=m.llm_temperature,
            embedding_provider=m.embedding_provider,
            embedding_model=m.embedding_model,
            embedding_api_key=m.embedding_api_key,
            embedding_dimensions=m.embedding_dimensions,
            whatsapp_phone_number_id=m.whatsapp_phone_number_id,
            whatsapp_access_token=m.whatsapp_access_token,
            whatsapp_verify_token=m.whatsapp_verify_token,
            whatsapp_app_secret=m.whatsapp_app_secret,
            telegram_bot_token=m.telegram_bot_token,
            telegram_webhook_secret=m.telegram_webhook_secret,
            bot_name=m.bot_name,
            bot_welcome_message=m.bot_welcome_message,
            bot_language=m.bot_language,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
