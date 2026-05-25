"""Tests for change password use case."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.auth.use_cases.change_password import ChangePassword, ChangePasswordUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthenticationError
from src.domain.tenants.entities import Tenant
from src.domain.users.entities import User
from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher
from src.infrastructure.persistence.postgres.database import async_session_factory

_HASHER = BcryptPasswordHasher(rounds=4)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password_success(client=None):
    async with async_session_factory() as session:
        uow = UnitOfWork(session)

        t = Tenant.create(name="CP", slug=f"cp-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        user = User.create(email=f"cp-{uuid4().hex[:8]}@t.com", hashed_password=_HASHER.hash("oldpass123"))
        await uow.users.save(user)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = ChangePasswordUseCase(uow=uow, password_hasher=_HASHER)
        await uc.execute(ChangePassword(user_id=user.id, old_password="oldpass123", new_password="newpass456"))
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        updated = await uow.users.get_by_id(user.id)
        assert updated is not None
        assert _HASHER.verify("newpass456", updated.hashed_password)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password_wrong_old(client=None):
    async with async_session_factory() as session:
        uow = UnitOfWork(session)

        t = Tenant.create(name="CPW", slug=f"cpw-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        user = User.create(email=f"cpw-{uuid4().hex[:8]}@t.com", hashed_password=_HASHER.hash("correct"))
        await uow.users.save(user)
        await uow.commit()
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        uc = ChangePasswordUseCase(uow=uow, password_hasher=_HASHER)
        with pytest.raises(AuthenticationError):
            await uc.execute(ChangePassword(user_id=user.id, old_password="wrong", new_password="new"))
