"""PostgreSQL Contact repository."""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.contacts.entities import Contact
from src.infrastructure.persistence.postgres.models.contact import ContactModel

logger = structlog.get_logger()


class PostgresContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_by_phone(
        self,
        tenant_id: UUID,
        phone: str,
        name: str | None = None,
    ) -> Contact:
        """Return existing contact or create one. Race-safe via retry on IntegrityError."""
        existing = await self._get_by_phone(tenant_id, phone)
        if existing is not None:
            return existing

        contact = Contact.create(tenant_id=tenant_id, phone=phone, name=name)
        try:
            self._session.add(self._to_model(contact))
            await self._session.flush()
            contact.mark_persisted()
        except IntegrityError:
            logger.debug("contact.get_or_create.race", phone=phone, tenant_id=str(tenant_id))
            await self._session.rollback()
            existing = await self._get_by_phone(tenant_id, phone)
            if existing is not None:
                return existing
            raise
        return contact

    async def get_by_telegram_user_id(
        self,
        tenant_id: UUID,
        telegram_user_id: str,
    ) -> Contact | None:
        stmt = select(ContactModel).where(
            ContactModel.tenant_id == tenant_id,
            ContactModel.telegram_user_id == telegram_user_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, contact: Contact) -> None:
        if contact.is_new:
            self._session.add(self._to_model(contact))
            await self._session.flush()
            contact.mark_persisted()
            return
        model = await self._session.get(ContactModel, contact.id)
        if model is None:
            self._session.add(self._to_model(contact))
            await self._session.flush()
            contact.mark_persisted()
            return
        model.name = contact.name
        model.email = contact.email
        model.phone = contact.phone
        model.telegram_user_id = contact.telegram_user_id
        model.updated_at = contact.updated_at

    async def get_by_id(self, contact_id: UUID) -> Contact | None:
        model = await self._session.get(ContactModel, contact_id)
        return self._to_entity(model) if model else None

    async def _get_by_phone(self, tenant_id: UUID, phone: str) -> Contact | None:
        stmt = select(ContactModel).where(
            ContactModel.tenant_id == tenant_id,
            ContactModel.phone == phone,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    @staticmethod
    def _to_model(c: Contact) -> ContactModel:
        return ContactModel(
            id=c.id,
            tenant_id=c.tenant_id,
            phone=c.phone,
            name=c.name,
            email=c.email,
            telegram_user_id=c.telegram_user_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )

    @staticmethod
    def _to_entity(m: ContactModel) -> Contact:
        return Contact(
            id=m.id,
            tenant_id=m.tenant_id,
            phone=m.phone,
            name=m.name,
            email=m.email,
            telegram_user_id=m.telegram_user_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
