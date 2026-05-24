"""Settings routes — owner manages their tenant's LLM + channel config."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from src.domain.shared.exceptions import AuthenticationError, EntityNotFoundError
from src.domain.tenant_config.entities import TenantConfig
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.drivers.api.v1.settings.schemas import (
    TenantConfigResponse,
    UpdateBotConfig,
    UpdateEmbeddingConfig,
    UpdateLLMConfig,
    UpdateTelegramConfig,
    UpdateWhatsAppConfig,
)

router = APIRouter(prefix="/settings", tags=["settings"])


async def _resolve_config(current_user: CurrentUser, uow: UnitOfWorkDep) -> tuple[UUID, TenantConfig]:
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    tenant_id = links[0].tenant_id
    config = await uow.tenant_configs.get_by_tenant_id(tenant_id)
    if config is None:
        raise EntityNotFoundError("Tenant configuration not found")
    return tenant_id, config


def _to_response(config: TenantConfig) -> TenantConfigResponse:
    mask = TenantConfig.mask_key
    return TenantConfigResponse(
        llm_provider=config.llm_provider.value,
        llm_model=config.llm_model,
        llm_api_key_masked=mask(config.llm_api_key),
        llm_max_tokens=config.llm_max_tokens,
        llm_temperature=config.llm_temperature,
        embedding_provider=config.embedding_provider,
        embedding_model=config.embedding_model,
        embedding_api_key_masked=mask(config.embedding_api_key),
        embedding_dimensions=config.embedding_dimensions,
        whatsapp_phone_number_id=config.whatsapp_phone_number_id,
        whatsapp_access_token_masked=mask(config.whatsapp_access_token),
        whatsapp_verify_token_masked=mask(config.whatsapp_verify_token),
        telegram_bot_token_masked=mask(config.telegram_bot_token),
        telegram_webhook_secret_masked=mask(config.telegram_webhook_secret),
        bot_name=config.bot_name,
        bot_welcome_message=config.bot_welcome_message,
        bot_language=config.bot_language,
    )


@router.get("", response_model=TenantConfigResponse)
async def get_settings(current_user: CurrentUser, uow: UnitOfWorkDep) -> TenantConfigResponse:
    _, config = await _resolve_config(current_user, uow)
    return _to_response(config)


@router.put("/llm", response_model=TenantConfigResponse)
async def update_llm(
    req: UpdateLLMConfig,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> TenantConfigResponse:
    _, config = await _resolve_config(current_user, uow)
    config.update_llm(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )
    await uow.tenant_configs.save(config)
    return _to_response(config)


@router.put("/embedding", response_model=TenantConfigResponse)
async def update_embedding(
    req: UpdateEmbeddingConfig,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> TenantConfigResponse:
    _, config = await _resolve_config(current_user, uow)
    config.update_embedding(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
        dimensions=req.dimensions,
    )
    await uow.tenant_configs.save(config)
    return _to_response(config)


@router.put("/whatsapp", response_model=TenantConfigResponse)
async def update_whatsapp(
    req: UpdateWhatsAppConfig,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> TenantConfigResponse:
    _, config = await _resolve_config(current_user, uow)
    config.update_whatsapp(
        phone_number_id=req.phone_number_id,
        access_token=req.access_token,
        verify_token=req.verify_token,
    )
    await uow.tenant_configs.save(config)
    return _to_response(config)


@router.put("/telegram", response_model=TenantConfigResponse)
async def update_telegram(
    req: UpdateTelegramConfig,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> TenantConfigResponse:
    _, config = await _resolve_config(current_user, uow)
    config.update_telegram(
        bot_token=req.bot_token,
        webhook_secret=req.webhook_secret,
    )
    await uow.tenant_configs.save(config)
    return _to_response(config)


@router.put("/bot", response_model=TenantConfigResponse)
async def update_bot(
    req: UpdateBotConfig,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> TenantConfigResponse:
    _, config = await _resolve_config(current_user, uow)
    config.update_bot(
        name=req.name,
        welcome_message=req.welcome_message,
        language=req.language,
    )
    await uow.tenant_configs.save(config)
    return _to_response(config)
