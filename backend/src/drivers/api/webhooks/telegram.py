"""Telegram webhook — receives updates from a per-tenant bot.

Verification: compares X-Telegram-Bot-Api-Secret-Token header against
the tenant's configured secret. Replies are sent via the TelegramAdapter
(shared httpx client, retry, HTML fallback).
"""

from __future__ import annotations

import hmac
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Header, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenants.value_objects import TenantStatus
from src.drivers.api.dependencies import get_session
from src.infrastructure.channels.cache import get_telegram_adapter
from src.infrastructure.channels.idempotency import is_duplicate_message

logger = structlog.get_logger()

# Sent when an asker messages with non-text content (voice/photo/etc.) — the v1
# agent only handles text, but we acknowledge rather than silently ignore.
_TEXT_ONLY_REPLY = "Sorry, I can only read text messages right now. Please type your question."

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/{tenant_id}/telegram")
async def telegram_webhook(
    tenant_id: str,
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> Response:
    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

    body: dict[str, Any] = await request.json()
    status = await _handle_telegram_post(tid, body, x_telegram_bot_api_secret_token, tenant_id)
    return Response(status_code=status)


def _parse_telegram_message(body: dict[str, Any]) -> tuple[str, str, str | None, str, str] | None:
    """Extract (text, telegram_user_id, sender_name, chat_id, message_id) or None."""
    message = body.get("message") or body.get("edited_message")
    if not message:
        return None
    from_user = message.get("from", {})
    telegram_user_id = str(from_user.get("id", ""))
    text = message.get("text", "")
    if not text or not telegram_user_id:
        return None
    chat_id = str(message.get("chat", {}).get("id", ""))
    raw_msg_id = message.get("message_id")
    # message_id is unique per chat — qualify with chat_id for global uniqueness.
    message_id = f"{chat_id}:{raw_msg_id}" if raw_msg_id is not None else ""
    return text, telegram_user_id, from_user.get("first_name"), chat_id, message_id


_TELEGRAM_CONTENT_KEYS = ("voice", "audio", "photo", "video", "document", "sticker", "location")


def _nontext_chat_id(body: dict[str, Any]) -> str | None:
    """Chat id of an inbound message carrying non-text *content* (voice/photo/…).

    Only fires for real media — empty text and service messages return None so we
    don't reply to them.
    """
    message = body.get("message") or body.get("edited_message")
    if not message or message.get("text"):
        return None
    if not any(key in message for key in _TELEGRAM_CONTENT_KEYS):
        return None
    return str(message.get("chat", {}).get("id", "")) or None


async def _validate_telegram_request(
    uow: UnitOfWork, tid: UUID, secret_header: str | None, tenant_id_raw: str
) -> TenantConfig | int:
    """Load config + verify the shared secret. Returns config or an HTTP status."""
    config = await uow.tenant_configs.get_by_tenant_id(tid)
    if config is None:
        return 404
    expected_secret = config.telegram_webhook_secret
    if not expected_secret or not secret_header or not hmac.compare_digest(secret_header, expected_secret):
        logger.warning("telegram.webhook.auth_failed", tenant_id=tenant_id_raw)
        return 403
    tenant = await uow.tenants.get_by_id(tid)
    if tenant is not None and tenant.status == TenantStatus.SUSPENDED:
        # Ack without processing so Telegram stops retrying a suspended tenant.
        logger.info("telegram.webhook.tenant_suspended", tenant_id=tenant_id_raw)
        return 200
    return config


async def _process_telegram_text(
    tid: UUID,
    uow: UnitOfWork,
    config: TenantConfig,
    parsed: tuple[str, str, str | None, str, str],
    tenant_id_raw: str,
) -> None:
    """Run the agent for a text message and send the reply back."""
    text, telegram_user_id, sender_name, chat_id, message_id = parsed
    # Telegram re-delivers updates until acked — skip duplicates.
    if await is_duplicate_message(tenant_id=tid, channel="telegram", message_id=message_id):
        logger.info("telegram.webhook.duplicate", tenant_id=tenant_id_raw, message_id=message_id)
        return
    result = await chat_with_agent(
        ChatInput(
            message=text,
            tenant_id=tid,
            channel=ConversationChannel.TELEGRAM,
            sender_identifier=telegram_user_id,
            sender_name=sender_name,
            provider_message_id=message_id,
        ),
        uow=uow,
    )
    await uow.commit()
    if not result.duplicate and config.telegram_bot_token and chat_id:
        adapter = await get_telegram_adapter(str(tid), tenant_config=config)
        await adapter.send_text(chat_id, result.response)


async def _handle_telegram_post(tid: UUID, body: dict[str, Any], secret_header: str | None, tenant_id_raw: str) -> int:
    parsed = _parse_telegram_message(body)
    nontext_chat_id = _nontext_chat_id(body) if parsed is None else None
    if parsed is None and nontext_chat_id is None:
        return 200

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            validated = await _validate_telegram_request(uow, tid, secret_header, tenant_id_raw)
            if isinstance(validated, int):
                return validated
            config = validated

            if parsed is None:
                # Non-text message — acknowledge instead of silently ignoring.
                if config.telegram_bot_token and nontext_chat_id:
                    adapter = await get_telegram_adapter(str(tid), tenant_config=config)
                    await adapter.send_text(nontext_chat_id, _TEXT_ONLY_REPLY)
                return 200

            await _process_telegram_text(tid, uow, config, parsed, tenant_id_raw)
        except Exception:
            await uow.rollback()
            logger.error("telegram.webhook.failed", tenant_id=tenant_id_raw, exc_info=True)

    return 200
