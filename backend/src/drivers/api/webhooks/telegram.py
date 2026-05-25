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
from src.infrastructure.channels.telegram import TelegramAdapter

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


async def _handle_telegram_post(tid: UUID, body: dict[str, Any], secret_header: str | None, tenant_id_raw: str) -> int:
    message = body.get("message") or body.get("edited_message")
    if not message:
        return 200

    from_user = message.get("from", {})
    telegram_user_id = str(from_user.get("id", ""))
    text = message.get("text", "")
    sender_name = from_user.get("first_name")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not telegram_user_id:
        return 200

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            config = await uow.tenant_configs.get_by_tenant_id(tid)
            if config is None:
                logger.warning("telegram.webhook.no_config", tenant_id=tenant_id_raw)
                return 404

            if config.telegram_webhook_secret and secret_header != config.telegram_webhook_secret:
                logger.warning("telegram.webhook.invalid_secret", tenant_id=tenant_id_raw)
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
                adapter = TelegramAdapter(tenant_config=config)  # type: ignore[arg-type]
                await adapter.send_text(chat_id, result.response)
        except Exception:
            await uow.rollback()
            logger.error("telegram.webhook.failed", tenant_id=tenant_id_raw, exc_info=True)

    return 200
