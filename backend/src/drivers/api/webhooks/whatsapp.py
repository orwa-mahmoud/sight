"""WhatsApp Cloud API webhook — receives messages from Meta.

Verification: GET with hub.verify_token matched against the tenant's
stored verify token. POST with X-Hub-Signature-256 HMAC-SHA256
verification. All credentials come from the tenant_configs table.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Header, Query, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.drivers.api.dependencies import get_session

logger = structlog.get_logger()

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
        if config and hub_mode == "subscribe" and hub_verify_token == config.whatsapp_verify_token:
            return Response(content=hub_challenge, media_type="text/plain")

    return Response(status_code=403)


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

    payload: dict[str, Any] = await request.json()
    text, sender_phone, sender_name, phone_number_id = _extract_message(payload)
    if not text or not sender_phone:
        return Response(status_code=200)

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            config = await uow.tenant_configs.get_by_tenant_id(tid)
            if config is None:
                return Response(status_code=404)

            if not _check_signature(body, x_hub_signature_256, config):
                return Response(status_code=403)

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

            if phone_number_id and config.whatsapp_access_token:
                await _send_reply(phone_number_id, sender_phone, result.response, config.whatsapp_access_token)
        except Exception:
            await uow.rollback()
            logger.error("whatsapp.webhook.failed", tenant_id=tenant_id, exc_info=True)

    return Response(status_code=200)


def _parse_tenant_id(raw: str) -> UUID | None:
    try:
        return UUID(raw)
    except ValueError:
        return None


def _extract_message(payload: dict[str, Any]) -> tuple[str, str, str | None, str | None]:
    """Extract text, sender_phone, sender_name, phone_number_id from Meta payload."""
    entry = (payload.get("entry") or [{}])[0]
    changes = (entry.get("changes") or [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])
    if not messages:
        return "", "", None, None
    msg = messages[0]
    sender_phone = msg.get("from", "")
    text = ""
    if msg.get("type") == "text":
        text = (msg.get("text") or {}).get("body", "")
    contacts = value.get("contacts", [])
    sender_name = contacts[0].get("profile", {}).get("name") if contacts else None
    phone_number_id = value.get("metadata", {}).get("phone_number_id")
    return text, sender_phone, sender_name, phone_number_id


def _check_signature(body: bytes, sig_header: str | None, config: Any) -> bool:
    """Verify HMAC if the tenant has a verify token configured."""
    if not config.whatsapp_access_token:
        return True
    app_secret = config.whatsapp_verify_token or ""
    if not app_secret:
        return True
    return _verify_signature(body, sig_header, app_secret)


def _verify_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def _send_reply(phone_number_id: str, to: str, text: str, access_token: str) -> None:
    """Send a text reply via WhatsApp Cloud API."""
    import httpx  # noqa: PLC0415

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://graph.facebook.com/v21.0/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
                timeout=10,
            )
    except Exception:
        logger.error("whatsapp.reply.failed", exc_info=True)
