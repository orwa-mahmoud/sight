"""ChangePassword use case — verify old password before updating."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.auth.ports import PasswordHasher
from src.domain.shared.exceptions import AuthenticationError, EntityNotFoundError


@dataclass(frozen=True, kw_only=True)
class ChangePassword:
    user_id: UUID
    old_password: str
    new_password: str


class ChangePasswordUseCase:
    def __init__(self, *, uow: UnitOfWork, password_hasher: PasswordHasher) -> None:
        self._uow = uow
        self._hasher = password_hasher

    async def execute(self, cmd: ChangePassword) -> None:
        user = await self._uow.users.get_by_id(cmd.user_id)
        if user is None:
            raise EntityNotFoundError("User not found", code="user.not_found")
        if not self._hasher.verify(cmd.old_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect", code="auth.current_password_incorrect")
        user.update_password(self._hasher.hash(cmd.new_password))
        await self._uow.users.save(user)
