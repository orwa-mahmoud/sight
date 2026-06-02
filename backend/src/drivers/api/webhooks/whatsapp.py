"""WhatsApp Cloud API webhook — receives messages from Meta.

Verification: GET with hub.verify_token matched against the tenant's
stored verify token. POST with X-Hub-Signature-256 HMAC-SHA256
verification using the tenant's whatsapp_app_secret. Replies are sent
via the WhatsAppAdapter (shared httpx client, retry, media support).
"""

from __future__ import annotations

import hmac
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Header, Query, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenants.value_objects import TenantStatus
from src.drivers.api.dependencies import get_session
from src.infrastructure.channels.cache import get_whatsapp_adapter
from src.infrastructure.channels.idempotency import is_duplicate_message
from src.infrastructure.channels.whatsapp import WhatsAppAdapter

logger = structlog.get_logger()

# Sent when an asker messages with non-text content (voice/image/etc.) — the v1
# agent only handles text, but we acknowledge rather than silently ignore.
_TEXT_ONLY_REPLY = "Sorry, I can only read text messages right now. Please type your question."

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks/{tenant_id}/whatsapp")
async def whatsapp_verify(
    tenant_id: str,
    hub_mode: Annotated[str, Query(alias="hub.mode")] = "",
    hub_verify_token: Annotated[str, Query(alias="hub.verify_token")] = "",
    hub_challenge: Annotated[str, Query(alias="hub.challenge")] = "",
) -> Response:
    """Meta webhook verification."""
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

    async for session in get_session():
        uow = UnitOfWork(session)
        config = await uow.tenant_configs.get_by_tenant_id(tid)
        if config and hub_mode == "subscribe" and _verify_token_matches(hub_verify_token, config.whatsapp_verify_token):
            return Response(content=hub_challenge, media_type="text/plain")

    return Response(status_code=403)


def _verify_token_matches(provided: str, expected: str | None) -> bool:
    """Constant-time compare of the Meta verify token (consistent with the POST HMAC check)."""
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided, expected)


@router.post("/webhooks/{tenant_id}/whatsapp")
async def whatsapp_webhook(
    tenant_id: str,
    request: Request,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> Response:
    body = await request.body()
    tid = _parse_tenant_id(tenant_id)
    if tid is None:
        return Response(status_code=400)

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        return Response(status_code=400)

    status = await _handle_whatsapp_post(tid, body, payload, x_hub_signature_256, tenant_id)
    return Response(status_code=status)


async def _validate_whatsapp_request(
    uow: UnitOfWork, tid: UUID, body: bytes, sig: str | None, tenant_id_raw: str
) -> TenantConfig | int:
    """Load + verify the request. Returns the config, or an HTTP status to reject with."""
    config = await uow.tenant_configs.get_by_tenant_id(tid)
    if config is None:
        return 404
    if not config.whatsapp_app_secret:
        logger.warning("whatsapp.webhook.no_app_secret", tenant_id=tenant_id_raw)
        return 403
    if not WhatsAppAdapter.verify_signature(body, sig or "", config.whatsapp_app_secret):
        logger.warning("whatsapp.webhook.invalid_signature", tenant_id=tenant_id_raw)
        return 403
    tenant = await uow.tenants.get_by_id(tid)
    if tenant is not None and tenant.status == TenantStatus.SUSPENDED:
        # Ack without processing so Meta stops retrying a suspended tenant.
        logger.info("whatsapp.webhook.tenant_suspended", tenant_id=tenant_id_raw)
        return 200
    return config


async def _handle_whatsapp_post(
    tid: UUID, body: bytes, payload: dict[str, Any], sig: str | None, tenant_id_raw: str
) -> int:
    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            validated = await _validate_whatsapp_request(uow, tid, body, sig, tenant_id_raw)
            if isinstance(validated, int):
                return validated
            config = validated

            adapter = await get_whatsapp_adapter(
                str(tid),
                phone_number_id=config.whatsapp_phone_number_id or "",
                access_token=config.whatsapp_access_token or "",
            )
            incoming = await adapter.parse_incoming(payload)

            if not incoming.sender_phone:
                return 200  # status update / non-message webhook — nothing to do

            # Meta delivers webhooks at least once — skip a message we've already
            # processed so the asker isn't answered (and billed) twice.
            if await is_duplicate_message(tenant_id=tid, channel="whatsapp", message_id=incoming.message_id):
                logger.info("whatsapp.webhook.duplicate", tenant_id=tenant_id_raw, message_id=incoming.message_id)
                return 200

            if not incoming.text:
                # Non-text message (voice/image/etc.) — acknowledge instead of
                # silently ignoring, so the asker isn't left wondering.
                await adapter.send_text(incoming.sender_phone, _TEXT_ONLY_REPLY)
                return 200

            result = await chat_with_agent(
                ChatInput(
                    message=incoming.text,
                    tenant_id=tid,
                    channel=ConversationChannel.WHATSAPP,
                    sender_identifier=incoming.sender_phone,
                    sender_name=None,
                ),
                uow=uow,
            )
            await uow.commit()
            await adapter.send_text(incoming.sender_phone, result.response)
        except Exception:
            await uow.rollback()
            logger.error("whatsapp.webhook.failed", tenant_id=tenant_id_raw, exc_info=True)

    return 200


def _parse_tenant_id(raw: str) -> UUID | None:
    try:
        return UUID(raw)
    except ValueError:
        return None
