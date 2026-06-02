"""Auth routes: register, login, /me, refresh."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from src.application.auth.commands import AuthenticateUser, RegisterOwner
from src.application.auth.use_cases.change_password import ChangePassword, ChangePasswordUseCase
from src.application.auth.use_cases.refresh_token import RefreshTokenUseCase
from src.bootstrap.container import (
    authenticate_user_use_case,
    get_jwt_service,
    get_password_hasher,
    get_user_by_id_use_case,
    register_owner_use_case,
)
from src.drivers.api.auth_cookie import COOKIE_NAME as _COOKIE_NAME
from src.drivers.api.auth_cookie import set_auth_cookie as _set_auth_cookie
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.drivers.api.middleware.rate_limit import limiter
from src.drivers.api.v1.auth.schemas import LoginRequest, MeResponse, RegisterRequest, TenantSummary, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest, uow: UnitOfWorkDep, response: Response) -> TokenResponse:
    cmd = RegisterOwner(
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        tenant_name=req.tenant_name,
        tenant_slug=req.tenant_slug,
    )
    result = await register_owner_use_case(uow).execute(cmd)
    _set_auth_cookie(response, result.access_token)
    return TokenResponse(access_token=result.access_token, user_id=result.user_id, tenant_id=result.tenant_id)


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest, uow: UnitOfWorkDep, response: Response) -> TokenResponse:
    cmd = AuthenticateUser(email=req.email, password=req.password)
    result = await authenticate_user_use_case(uow).execute(cmd)
    _set_auth_cookie(response, result.access_token)
    return TokenResponse(access_token=result.access_token, user_id=result.user_id, tenant_id=result.tenant_id)


@router.get("/me")
async def me(current_user: CurrentUser, uow: UnitOfWorkDep) -> MeResponse:
    dto = await get_user_by_id_use_case(uow).execute(current_user.id)
    return MeResponse(
        id=dto.id,
        email=dto.email,
        full_name=dto.full_name,
        is_active=dto.is_active,
        is_platform_admin=dto.is_platform_admin,
        tenant=TenantSummary(id=dto.tenant_id, slug=dto.tenant_slug, name=dto.tenant_name, role=dto.role),
    )


@router.post("/refresh")
async def refresh(current_user: CurrentUser, uow: UnitOfWorkDep, response: Response) -> TokenResponse:
    # Sliding-session re-issue: mint a fresh access token for the already
    # authenticated user. This is NOT a refresh-token grant — there is no
    # long-lived refresh token yet (JWT_REFRESH_TOKEN_EXPIRE_DAYS is reserved).
    uc = RefreshTokenUseCase(uow=uow, jwt_service=get_jwt_service())
    result = await uc.execute(current_user.id)
    _set_auth_cookie(response, result.access_token)
    return TokenResponse(access_token=result.access_token, user_id=result.user_id, tenant_id=result.tenant_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, path="/")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(req: ChangePasswordRequest, current_user: CurrentUser, uow: UnitOfWorkDep) -> None:
    await ChangePasswordUseCase(uow=uow, password_hasher=get_password_hasher()).execute(
        ChangePassword(user_id=current_user.id, old_password=req.old_password, new_password=req.new_password)
    )
