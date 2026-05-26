"""Notification routing adapter -- resolves delivery channel via DB lookups.

Generic -- works for any entity type. Callers provide tenant_id + recipient details.

Fallback chain:
1. Most recent conversation for recipient+tenant -> send there
2. Tenant has WhatsApp configured -> create WhatsApp thread
3. Recipient has telegram_user_id -> create Telegram thread
4. Raise NotificationRoutingError

Ported from PropertyBot. Adapted to use frontdesk models (Contact instead of
Client, User for owner/user recipients).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.domain.notifications.ports import NotificationRoutingError, NotificationRoutingPort, ResolvedRoute
from src.infrastructure.persistence.postgres.models.contact import ContactModel
from src.infrastructure.persistence.postgres.models.conversation import ConversationModel
from src.infrastructure.persistence.postgres.models.tenant_config import TenantConfigModel
from src.infrastructure.persistence.postgres.models.user import UserModel

logger = structlog.get_logger()


class NotificationRoutingAdapter(NotificationRoutingPort):
    """Resolves the best delivery channel for a notification recipient."""

    def __init__(self, session_factory: async_sessionmaker[Any]) -> None:
        self._session_factory = session_factory

    async def resolve_route(
        self,
        *,
        tenant_id: uuid.UUID,
        recipient_id: uuid.UUID,
        recipient_type: str,
    ) -> ResolvedRoute:
        async with self._session_factory() as session:
            phone, telegram_uid = await self._load_recipient_contact(
                session,
                recipient_id,
                recipient_type,
                tenant_id,
            )

            # Step 1: Find most recent conversation for this recipient
            route = await self._try_existing_conversation(session, recipient_id, tenant_id)
            if route:
                logger.debug(
                    "routing.found_conversation",
                    channel=route.channel,
                    thread_id=route.thread_id,
                )
                return route

            # Step 2: Check if tenant has WhatsApp configured
            route = await self._try_whatsapp(session, tenant_id, recipient_id, phone, recipient_type)
            if route:
                logger.debug("routing.fallback_whatsapp", tenant_id=str(tenant_id))
                return route

            # Step 3: Check Telegram
            route = self._try_telegram(tenant_id, recipient_id, telegram_uid, recipient_type)
            if route:
                logger.debug("routing.fallback_telegram", tenant_id=str(tenant_id))
                return route

            # Step 4: All failed
            raise NotificationRoutingError(
                f"No delivery channel for {recipient_type} {recipient_id}",
                context_data={
                    "tenant_id": str(tenant_id),
                    "recipient_id": str(recipient_id),
                    "recipient_type": recipient_type,
                    "phone": phone,
                    "telegram_user_id": telegram_uid,
                },
            )

    async def _load_recipient_contact(
        self,
        session: Any,
        recipient_id: uuid.UUID,
        recipient_type: str,
        tenant_id: uuid.UUID,
    ) -> tuple[str | None, str | None]:
        """Load phone + telegram_user_id for a recipient, scoped by tenant."""
        if recipient_type in ("owner", "user"):
            user = (await session.execute(select(UserModel).where(UserModel.id == recipient_id))).scalar_one_or_none()
            if not user:
                raise NotificationRoutingError(f"User {recipient_id} not found")
            return getattr(user, "phone", None), getattr(user, "telegram_user_id", None)

        contact = (
            await session.execute(
                select(ContactModel).where(ContactModel.id == recipient_id, ContactModel.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()
        if not contact:
            raise NotificationRoutingError(f"Contact {recipient_id} not found for tenant")
        return contact.phone, getattr(contact, "telegram_user_id", None)

    async def _try_existing_conversation(
        self,
        session: Any,
        participant_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ResolvedRoute | None:
        """Step 1: Find most recent conversation for this participant+tenant."""
        result = await session.execute(
            select(ConversationModel)
            .where(
                ConversationModel.participant_id == participant_id,
                ConversationModel.tenant_id == tenant_id,
            )
            .order_by(ConversationModel.last_message_at.desc().nullslast())
            .limit(1)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            return None

        return ResolvedRoute(
            channel=conv.channel,
            thread_id=conv.thread_id,
            conversation_id=conv.id,
            tenant_id=tenant_id,
            recipient_id=participant_id,
        )

    async def _try_whatsapp(
        self,
        session: Any,
        tenant_id: uuid.UUID,
        recipient_id: uuid.UUID,
        phone: str | None,
        recipient_type: str,
    ) -> ResolvedRoute | None:
        """Step 2: Check if tenant has WhatsApp configured and recipient has a phone."""
        if not phone:
            return None

        config = (
            await session.execute(select(TenantConfigModel).where(TenantConfigModel.tenant_id == tenant_id))
        ).scalar_one_or_none()
        if not config:
            return None

        if not config.whatsapp_phone_number_id or not config.whatsapp_access_token:
            return None

        prefix = "contact" if recipient_type == "contact" else "user"
        thread_id = f"{prefix}:{tenant_id}:{phone}:whatsapp"

        return ResolvedRoute(
            channel="whatsapp",
            thread_id=thread_id,
            tenant_id=tenant_id,
            recipient_id=recipient_id,
        )

    def _try_telegram(
        self,
        tenant_id: uuid.UUID,
        recipient_id: uuid.UUID,
        telegram_user_id: str | None,
        recipient_type: str,
    ) -> ResolvedRoute | None:
        """Step 3: Check if recipient has a Telegram user ID."""
        if not telegram_user_id:
            return None

        prefix = "contact" if recipient_type == "contact" else "user"
        thread_id = f"{prefix}:{tenant_id}:{telegram_user_id}:telegram"

        return ResolvedRoute(
            channel="telegram",
            thread_id=thread_id,
            tenant_id=tenant_id,
            recipient_id=recipient_id,
        )
