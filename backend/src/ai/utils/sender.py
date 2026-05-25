"""Sender resolution — resolve channel user to a Contact.

Simplified from PropertyBot: no tenant-user check, no lead management.
Just create-or-fetch a Contact so the conversation gets a real participant_id.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel

logger = structlog.get_logger()


async def resolve_sender(
    *,
    tenant_id: UUID,
    channel: ConversationChannel,
    sender_identifier: str,
    sender_name: str | None = None,
    uow: UnitOfWork,
) -> UUID | None:
    """Resolve sender identity to a contact_id.

    - Telegram: look up phone from telegram_phones table, then get_or_create contact.
    - WhatsApp: get_or_create contact by phone directly.
    - Other channels: get_or_create contact by identifier as phone.

    Returns the contact UUID, or None if we cannot resolve (e.g. Telegram user
    who hasn't shared their phone yet).
    """
    if channel == ConversationChannel.TELEGRAM:
        return await _resolve_telegram_sender(
            tenant_id=tenant_id,
            telegram_user_id=sender_identifier,
            sender_name=sender_name,
            uow=uow,
        )

    if channel in (ConversationChannel.WHATSAPP,):
        return await _resolve_phone_sender(
            tenant_id=tenant_id,
            phone=sender_identifier,
            name=sender_name,
            uow=uow,
        )

    # API / web / owner_dashboard — treat identifier as a phone-like key
    return await _resolve_phone_sender(
        tenant_id=tenant_id,
        phone=sender_identifier,
        name=sender_name,
        uow=uow,
    )


async def _resolve_telegram_sender(
    *,
    tenant_id: UUID,
    telegram_user_id: str,
    sender_name: str | None,
    uow: UnitOfWork,
) -> UUID | None:
    """Resolve a Telegram user to a contact.

    1. Check telegram_phones for a stored phone mapping.
    2. If phone found -> get_or_create contact by phone, link telegram_user_id.
    3. If no phone -> register the telegram_user_id (phone=NULL), return None.
    """
    phone = await uow.telegram_phones.get_or_register(telegram_user_id)
    if not phone:
        # User hasn't shared their phone yet.  The contact cannot be created
        # without a phone (our unique key), so return None.
        logger.info("sender.telegram.no_phone", telegram_user_id=telegram_user_id)
        return None

    contact = await uow.contacts.get_or_create_by_phone(
        tenant_id=tenant_id,
        phone=phone,
        name=sender_name,
    )

    # Link Telegram user ID if not already linked
    if contact.telegram_user_id != telegram_user_id:
        contact.link_telegram(telegram_user_id)
        await uow.contacts.save(contact)

    return contact.id


async def _resolve_phone_sender(
    *,
    tenant_id: UUID,
    phone: str,
    name: str | None,
    uow: UnitOfWork,
) -> UUID | None:
    """Get-or-create a contact by phone number."""
    try:
        contact = await uow.contacts.get_or_create_by_phone(
            tenant_id=tenant_id,
            phone=phone,
            name=name,
        )
        return contact.id
    except Exception:
        logger.error("sender.resolve_phone_failed", phone=phone, tenant_id=str(tenant_id), exc_info=True)
        return None
