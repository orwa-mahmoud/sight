"""Minimal DI container — builds use cases from primitives.

Per request, a session is opened, a UoW wraps it, and the container builds
whichever use cases the route needs. Cross-request singletons (hasher,
JWT service) are cached at module level.
"""

from __future__ import annotations

from functools import lru_cache

from src.application.admin.use_cases.list_tenants import ListTenantsForAdmin
from src.application.admin.use_cases.list_users import ListUsersForAdmin
from src.application.admin.use_cases.set_platform_admin import SetPlatformAdmin
from src.application.admin.use_cases.set_tenant_active import SetTenantActive
from src.application.admin.use_cases.set_user_active import SetUserActive
from src.application.auth.use_cases.authenticate_user import AuthenticateUserUseCase
from src.application.auth.use_cases.get_user_by_id import GetUserByIdUseCase
from src.application.auth.use_cases.register_owner import RegisterOwnerUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher
from src.infrastructure.auth.jwt_service import JwtService


@lru_cache
def get_password_hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


@lru_cache
def get_jwt_service() -> JwtService:
    settings = get_settings()
    return JwtService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    )


def register_owner_use_case(uow: UnitOfWork) -> RegisterOwnerUseCase:
    return RegisterOwnerUseCase(
        uow=uow,
        password_hasher=get_password_hasher(),
        jwt_service=get_jwt_service(),
    )


def authenticate_user_use_case(uow: UnitOfWork) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(
        uow=uow,
        password_hasher=get_password_hasher(),
        jwt_service=get_jwt_service(),
    )


def get_user_by_id_use_case(uow: UnitOfWork) -> GetUserByIdUseCase:
    return GetUserByIdUseCase(uow=uow)


# ── Admin (platform super-admin) ──────────────────────────────────


def list_tenants_for_admin_use_case(uow: UnitOfWork) -> ListTenantsForAdmin:
    return ListTenantsForAdmin(uow=uow)


def list_users_for_admin_use_case(uow: UnitOfWork) -> ListUsersForAdmin:
    return ListUsersForAdmin(uow=uow)


def set_tenant_active_use_case(uow: UnitOfWork) -> SetTenantActive:
    return SetTenantActive(uow=uow)


def set_user_active_use_case(uow: UnitOfWork) -> SetUserActive:
    return SetUserActive(uow=uow)


def set_platform_admin_use_case(uow: UnitOfWork) -> SetPlatformAdmin:
    return SetPlatformAdmin(uow=uow)
