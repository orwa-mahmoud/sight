"""WhatsApp Cloud API webhook — receives messages from Meta.

Verification: GET request with hub.verify_token for webhook registration.
Inbound: POST with X-Hub-Signature-256 HMAC-SHA256 verification against
the app secret. Message + sender phone extracted from Meta's standard
webhook payload structure.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import structlog
from fastapi import APIRouter, Header, Query, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.domain.conversations.value_objects import ConversationChannel
from src.drivers.api.dependencies import get_session

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks/{tenant_id}/whatsapp")
async def whatsapp_verify(
    tenant_id: str,
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """Meta webhook verification — echo the challenge if the token matches."""
    settings = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhooks/{tenant_id}/whatsapp")
async def whatsapp_webhook(
    tenant_id: str,
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> Response:
    body = await request.body()

    settings = get_settings()
    if settings.whatsapp_app_secret and not _verify_signature(body, x_hub_signature_256, settings.whatsapp_app_secret):
        logger.warning("whatsapp.webhook.invalid_signature", tenant_id=tenant_id)
        return Response(status_code=403)

    payload: dict[str, Any] = await request.json()

    # Extract message from Meta's nested structure.
    entry = (payload.get("entry") or [{}])[0]
    changes = (entry.get("changes") or [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])
    if not messages:
        return Response(status_code=200)

    msg = messages[0]
    sender_phone = msg.get("from", "")
    text = ""
    if msg.get("type") == "text":
        text = (msg.get("text") or {}).get("body", "")

    if not text or not sender_phone:
        return Response(status_code=200)

    # Extract sender name from contacts if available.
    contacts = value.get("contacts", [])
    sender_name = None
    if contacts:
        profile = contacts[0].get("profile", {})
        sender_name = profile.get("name")

    from uuid import UUID  # noqa: PLC0415

    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            result = await chat_with_agent(
                ChatInput(
                    message=text,
                    tenant_id=tid,
                    channel=ConversationChannel.WHATSAPP,
                    sender_identifier=sender_phone,
                    sender_name=sender_name,
                ),
                uow=uow,
            )
            await uow.commit()

            # Send reply back via WhatsApp Cloud API.
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            if phone_number_id:
                await _send_whatsapp_reply(
                    phone_number_id=phone_number_id,
                    to=sender_phone,
                    text=result.response,
                    tenant_id=tenant_id,
                )
        except Exception:
            await uow.rollback()
            logger.error("whatsapp.webhook.failed", tenant_id=tenant_id, exc_info=True)

    return Response(status_code=200)


def _verify_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def _send_whatsapp_reply(
    *,
    phone_number_id: str,
    to: str,
    text: str,
    tenant_id: str,
) -> None:
    """Send a text reply via WhatsApp Cloud API. Best-effort."""
    import httpx  # noqa: PLC0415

    # Per-tenant access token would come from the tenant_config table.
    access_token = ""  # resolve from tenant config in production
    if not access_token:
        logger.warning("whatsapp.reply.no_access_token", tenant_id=tenant_id)
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://graph.facebook.com/v21.0/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": text},
                },
                timeout=10,
            )
    except Exception:
        logger.error("whatsapp.reply.failed", tenant_id=tenant_id, exc_info=True)
