"""Auth routes: register, login, /me."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.application.auth.commands import AuthenticateUser, RegisterOwner
from src.bootstrap.container import (
    authenticate_user_use_case,
    get_user_by_id_use_case,
    register_owner_use_case,
)
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.drivers.api.v1.auth.schemas import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TenantSummary,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, uow: UnitOfWorkDep) -> TokenResponse:
    cmd = RegisterOwner(
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        tenant_name=req.tenant_name,
        tenant_slug=req.tenant_slug,
    )
    result = await register_owner_use_case(uow).execute(cmd)
    return TokenResponse(
        access_token=result.access_token,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, uow: UnitOfWorkDep) -> TokenResponse:
    cmd = AuthenticateUser(email=req.email, password=req.password)
    result = await authenticate_user_use_case(uow).execute(cmd)
    return TokenResponse(
        access_token=result.access_token,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
    )


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser, uow: UnitOfWorkDep) -> MeResponse:
    dto = await get_user_by_id_use_case(uow).execute(current_user.id)
    return MeResponse(
        id=dto.id,
        email=dto.email,
        full_name=dto.full_name,
        is_active=dto.is_active,
        tenant=TenantSummary(
            id=dto.tenant_id,
            slug=dto.tenant_slug,
            name=dto.tenant_name,
            role=dto.role,
        ),
    )
