"""Telegram webhook — receives updates from a per-tenant bot.

Verification: compares X-Telegram-Bot-Api-Secret-Token header against
the tenant's configured secret. Replies are sent via the TelegramAdapter
(shared httpx client, retry, HTML fallback).
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Header, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.drivers.api.dependencies import get_session
from src.infrastructure.channels.cache import get_telegram_adapter

logger = structlog.get_logger()

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


def _parse_telegram_message(body: dict[str, Any]) -> tuple[str, str, str | None, str] | None:
    """Extract (text, telegram_user_id, sender_name, chat_id) or None if no actionable message."""
    message = body.get("message") or body.get("edited_message")
    if not message:
        return None
    from_user = message.get("from", {})
    telegram_user_id = str(from_user.get("id", ""))
    text = message.get("text", "")
    if not text or not telegram_user_id:
        return None
    return text, telegram_user_id, from_user.get("first_name"), str(message.get("chat", {}).get("id", ""))


async def _handle_telegram_post(tid: UUID, body: dict[str, Any], secret_header: str | None, tenant_id_raw: str) -> int:
    parsed = _parse_telegram_message(body)
    if not parsed:
        return 200
    text, telegram_user_id, sender_name, chat_id = parsed

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            config = await uow.tenant_configs.get_by_tenant_id(tid)
            if config is None:
                return 404

            if not config.telegram_webhook_secret or secret_header != config.telegram_webhook_secret:
                logger.warning("telegram.webhook.auth_failed", tenant_id=tenant_id_raw)
                return 403

            result = await chat_with_agent(
                ChatInput(
                    message=text,
                    tenant_id=tid,
                    channel=ConversationChannel.TELEGRAM,
                    sender_identifier=telegram_user_id,
                    sender_name=sender_name,
                ),
                uow=uow,
            )
            await uow.commit()

            if config.telegram_bot_token and chat_id:
                adapter = await get_telegram_adapter(str(tid), tenant_config=config)
                await adapter.send_text(chat_id, result.response)
        except Exception:
            await uow.rollback()
            logger.error("telegram.webhook.failed", tenant_id=tenant_id_raw, exc_info=True)

    return 200
