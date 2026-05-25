"""Unit tests for PostgresUserTenantRepository — save update-path."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.users.entities import UserTenant
from src.domain.users.value_objects import UserTenantRole
from src.infrastructure.persistence.postgres.repositories.user_tenant_repo import PostgresUserTenantRepository


def _make_link(
    *,
    user_id: UUID | None = None,
    tenant_id: UUID | None = None,
    role: UserTenantRole = UserTenantRole.OWNER,
) -> UserTenant:
    return UserTenant.create(
        user_id=user_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        role=role,
    )


@pytest.mark.asyncio
async def test_save_existing_not_found_inserts() -> None:
    """When session.get returns None for a persisted link, insert it."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()  # add is sync

    repo = PostgresUserTenantRepository(session)
    link = _make_link()
    link.mark_persisted()

    await repo.save(link)

    session.get.assert_called_once()
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_save_existing_found_updates_role() -> None:
    """When session.get returns a model, update its role."""
    existing_model = MagicMock()
    session = AsyncMock()
    session.get = AsyncMock(return_value=existing_model)

    repo = PostgresUserTenantRepository(session)
    link = _make_link(role=UserTenantRole.STAFF)
    link.mark_persisted()

    await repo.save(link)

    assert existing_model.role == UserTenantRole.STAFF.value
    session.add.assert_not_called()


def test_to_model_maps_all_fields() -> None:
    link = _make_link()
    model = PostgresUserTenantRepository._to_model(link)

    assert model.id == link.id
    assert model.user_id == link.user_id
    assert model.tenant_id == link.tenant_id
    assert model.role == UserTenantRole.OWNER.value
    assert model.joined_at == link.joined_at


def test_to_entity_maps_all_fields() -> None:
    model = MagicMock()
    model.id = uuid4()
    model.user_id = uuid4()
    model.tenant_id = uuid4()
    model.role = UserTenantRole.STAFF.value
    model.joined_at = datetime.now(UTC)

    entity = PostgresUserTenantRepository._to_entity(model)

    assert entity.id == model.id
    assert entity.user_id == model.user_id
    assert entity.role == UserTenantRole.STAFF
