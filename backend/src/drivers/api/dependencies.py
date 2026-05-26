"""Shared FastAPI dependencies — DB session, UoW, current user."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.shared.unit_of_work import UnitOfWork
from src.bootstrap.container import get_jwt_service
from src.domain.shared.exceptions import AuthenticationError
from src.domain.users.entities import User
from src.infrastructure.persistence.postgres.database import async_session_factory

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session that commits on success and rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> UnitOfWork:
    return UnitOfWork(session)


async def get_current_user(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> User:
    if not token:
        raise AuthenticationError("Missing bearer token")

    payload = get_jwt_service().decode(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Token missing subject")

    try:
        user_id = UUID(sub)
    except ValueError:
        raise AuthenticationError("Invalid token subject")  # noqa: B904
    user = await uow.users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User no longer exists or is disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_uow)]
