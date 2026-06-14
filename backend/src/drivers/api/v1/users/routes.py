"""User profile routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep
from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher

router = APIRouter(prefix="/users", tags=["users"])

_hasher = BcryptPasswordHasher()


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    # Required when changing the password — re-auth so a hijacked session (or a
    # CSRF on this cookie-authed endpoint) can't silently take over the account.
    current_password: str | None = Field(default=None, max_length=128)


class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str | None


@router.put("/me")
async def update_profile(
    req: UpdateProfileRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> ProfileResponse:
    user = await uow.users.get_by_id(current_user.id)
    if not user:
        raise AuthenticationError("User not found")
    if req.full_name is not None:
        user.full_name = req.full_name.strip() or user.full_name
        user.updated_at = datetime.now(UTC)
    if req.password is not None:
        if not req.current_password or not _hasher.verify(req.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect", code="auth.invalid_credentials")
        user.update_password(_hasher.hash(req.password))
        user.updated_at = datetime.now(UTC)
    await uow.users.save(user)
    return ProfileResponse(id=str(user.id), email=user.email, full_name=user.full_name)
