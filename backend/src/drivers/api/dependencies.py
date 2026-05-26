"""Shared FastAPI dependencies — DB session, UoW, current user."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
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


_COOKIE_NAME = "frontdesk_token"


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> User:
    if not token:
        token = request.cookies.get(_COOKIE_NAME)
    if not token:
        raise AuthenticationError("Missing authentication")

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


async def resolve_tenant_id(current_user: User, uow: UnitOfWork) -> UUID:
    """Resolve the tenant ID for the current user. Shared across route files."""
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    return links[0].tenant_id
