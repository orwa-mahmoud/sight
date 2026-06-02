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
from src.domain.shared.exceptions import AuthenticationError, AuthorizationError
from src.domain.tenants.value_objects import TenantStatus
from src.domain.users.entities import User
from src.domain.users.value_objects import UserTenantRole
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
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc
    user = await uow.users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("User no longer exists or is disabled")

    # Tenant-suspension enforcement: a suspended tenant locks out its members,
    # including on already-issued sessions. Platform admins bypass this so they
    # can always reach the admin console.
    if not user.is_platform_admin:
        tenant_id_claim = payload.get("tenant_id")
        if tenant_id_claim:
            tenant = await uow.tenants.get_by_id(UUID(tenant_id_claim))
            if tenant is not None and tenant.status == TenantStatus.SUSPENDED:
                raise AuthenticationError("Tenant is suspended", code="auth.tenant_suspended")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_uow)]


def require_platform_admin(current_user: CurrentUser) -> User:
    """Guard: only platform super-admins may pass."""
    if not current_user.is_platform_admin:
        raise AuthorizationError("Platform admin privileges required")
    return current_user


async def require_owner(current_user: CurrentUser, uow: UnitOfWorkDep) -> User:
    """Guard: the caller must be the OWNER of their tenant."""
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthorizationError("User is not associated with any tenant")
    if links[0].role != UserTenantRole.OWNER:
        raise AuthorizationError("Owner privileges required")
    return current_user


PlatformAdmin = Annotated[User, Depends(require_platform_admin)]
TenantOwner = Annotated[User, Depends(require_owner)]


async def resolve_tenant_id(current_user: User, uow: UnitOfWork) -> UUID:
    """Resolve the tenant ID for the current user. Shared across route files."""
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    return links[0].tenant_id
