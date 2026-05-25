"""Unit tests for PostgresContactRepository.

Covers: get_or_create_by_phone, get_by_telegram_user_id, save, _to_model, _to_entity, get_by_id.
Mocks AsyncSession to avoid real DB.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.domain.contacts.entities import Contact
from src.infrastructure.persistence.postgres.models.contact import ContactModel
from src.infrastructure.persistence.postgres.repositories.contact_repo import PostgresContactRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contact(
    *,
    tenant_id=None,
    phone: str | None = "+971501234567",
    name: str | None = "Test",
    email: str | None = None,
    telegram_user_id: str | None = None,
) -> Contact:
    return Contact.create(
        tenant_id=tenant_id or uuid4(),
        phone=phone,
        name=name,
        email=email,
        telegram_user_id=telegram_user_id,
    )


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_contact_model(
    *,
    tenant_id=None,
    phone: str | None = "+971501234567",
    name: str | None = "Test",
    email: str | None = None,
    telegram_user_id: str | None = None,
) -> ContactModel:
    now = datetime.now(UTC)
    return ContactModel(
        id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        phone=phone,
        name=name,
        email=email,
        telegram_user_id=telegram_user_id,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# _to_model / _to_entity
# ---------------------------------------------------------------------------


class TestToModel:
    def test_maps_all_fields(self) -> None:
        contact = _make_contact(
            phone="+123",
            name="Alice",
            email="alice@example.com",
            telegram_user_id="tg_a",
        )
        model = PostgresContactRepository._to_model(contact)

        assert model.id == contact.id
        assert model.tenant_id == contact.tenant_id
        assert model.phone == "+123"
        assert model.name == "Alice"
        assert model.email == "alice@example.com"
        assert model.telegram_user_id == "tg_a"
        assert model.created_at == contact.created_at
        assert model.updated_at == contact.updated_at


class TestToEntity:
    def test_maps_all_fields(self) -> None:
        model = _make_contact_model(
            phone="+456",
            name="Bob",
            email="bob@example.com",
            telegram_user_id="tg_b",
        )
        entity = PostgresContactRepository._to_entity(model)

        assert entity.id == model.id
        assert entity.tenant_id == model.tenant_id
        assert entity.phone == "+456"
        assert entity.name == "Bob"
        assert entity.email == "bob@example.com"
        assert entity.telegram_user_id == "tg_b"
        assert entity.created_at == model.created_at
        assert entity.updated_at == model.updated_at

    def test_roundtrip_preserves_data(self) -> None:
        contact = _make_contact(phone="+789", name="Charlie", telegram_user_id="tg_c")
        model = PostgresContactRepository._to_model(contact)
        restored = PostgresContactRepository._to_entity(model)

        assert restored.id == contact.id
        assert restored.phone == contact.phone
        assert restored.name == contact.name
        assert restored.telegram_user_id == contact.telegram_user_id


# ---------------------------------------------------------------------------
# get_or_create_by_phone
# ---------------------------------------------------------------------------


class TestGetOrCreateByPhone:
    @pytest.mark.asyncio
    async def test_returns_existing_contact(self) -> None:
        """When phone already exists for tenant, returns the existing entity."""
        tenant_id = uuid4()
        model = _make_contact_model(tenant_id=tenant_id, phone="+123", name="Existing")

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(model))

        repo = PostgresContactRepository(session)
        contact = await repo.get_or_create_by_phone(tenant_id, "+123", name="Ignored")

        assert contact.phone == "+123"
        assert contact.name == "Existing"
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_contact_when_none_exists(self) -> None:
        """No existing contact -> creates a new one, flushes, marks persisted."""
        tenant_id = uuid4()

        session = AsyncMock()
        session.add = MagicMock()  # sync method on real AsyncSession
        session.execute = AsyncMock(return_value=_scalar_result(None))
        session.flush = AsyncMock()

        repo = PostgresContactRepository(session)
        contact = await repo.get_or_create_by_phone(tenant_id, "+999", name="New")

        assert contact.phone == "+999"
        assert contact.name == "New"
        assert contact.is_new is False  # mark_persisted called
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_race_condition_retries_on_integrity_error(self) -> None:
        """IntegrityError on insert -> rolls back, re-fetches existing."""
        tenant_id = uuid4()
        existing_model = _make_contact_model(tenant_id=tenant_id, phone="+111")

        session = AsyncMock()
        session.add = MagicMock()
        # First execute: _get_by_phone returns None (not found)
        # After rollback, second execute: _get_by_phone returns the existing
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(None),
                _scalar_result(existing_model),
            ],
        )
        session.flush = AsyncMock(
            side_effect=IntegrityError("dup", params=None, orig=Exception()),
        )
        session.rollback = AsyncMock()

        repo = PostgresContactRepository(session)
        contact = await repo.get_or_create_by_phone(tenant_id, "+111")

        assert contact.phone == "+111"
        session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_race_condition_raises_if_refetch_also_fails(self) -> None:
        """IntegrityError + re-fetch returns None -> re-raises."""
        tenant_id = uuid4()

        session = AsyncMock()
        session.add = MagicMock()
        session.execute = AsyncMock(
            side_effect=[_scalar_result(None), _scalar_result(None)],
        )
        session.flush = AsyncMock(
            side_effect=IntegrityError("dup", params=None, orig=Exception()),
        )
        session.rollback = AsyncMock()

        repo = PostgresContactRepository(session)
        with pytest.raises(IntegrityError):
            await repo.get_or_create_by_phone(tenant_id, "+111")


# ---------------------------------------------------------------------------
# get_by_telegram_user_id
# ---------------------------------------------------------------------------


class TestGetByTelegramUserId:
    @pytest.mark.asyncio
    async def test_returns_entity_when_found(self) -> None:
        tenant_id = uuid4()
        model = _make_contact_model(tenant_id=tenant_id, telegram_user_id="tg_1")

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(model))

        repo = PostgresContactRepository(session)
        contact = await repo.get_by_telegram_user_id(tenant_id, "tg_1")

        assert contact is not None
        assert contact.telegram_user_id == "tg_1"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        repo = PostgresContactRepository(session)
        contact = await repo.get_by_telegram_user_id(uuid4(), "tg_ghost")

        assert contact is None


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


class TestSave:
    @pytest.mark.asyncio
    async def test_save_new_contact_adds_and_flushes(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        contact = _make_contact()
        assert contact.is_new is True

        repo = PostgresContactRepository(session)
        await repo.save(contact)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert contact.is_new is False

    @pytest.mark.asyncio
    async def test_save_existing_contact_updates_model(self) -> None:
        """Existing contact (is_new=False) with model in DB -> updates fields."""
        contact = _make_contact(phone="+old")
        contact.mark_persisted()
        contact.phone = "+new"

        existing_model = MagicMock()
        session = AsyncMock()
        session.get = AsyncMock(return_value=existing_model)

        repo = PostgresContactRepository(session)
        await repo.save(contact)

        assert existing_model.phone == "+new"
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_existing_contact_model_not_in_db(self) -> None:
        """Existing contact (is_new=False) but session.get returns None -> re-inserts."""
        contact = _make_contact()
        contact.mark_persisted()

        session = AsyncMock()
        session.add = MagicMock()
        session.get = AsyncMock(return_value=None)
        session.flush = AsyncMock()

        repo = PostgresContactRepository(session)
        await repo.save(contact)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert contact.is_new is False


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetById:
    @pytest.mark.asyncio
    async def test_returns_entity_when_found(self) -> None:
        model = _make_contact_model()
        session = AsyncMock()
        session.get = AsyncMock(return_value=model)

        repo = PostgresContactRepository(session)
        contact = await repo.get_by_id(model.id)

        assert contact is not None
        assert contact.id == model.id

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        repo = PostgresContactRepository(session)
        contact = await repo.get_by_id(uuid4())

        assert contact is None
