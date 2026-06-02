"""SetUserActive — platform admin disables or enables a user login."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import EntityNotFoundError, InvalidOperationError


class SetUserActive:
    """Deactivate (active=False) or activate (active=True) a user. Idempotent.

    Guards against lockout: an admin cannot deactivate their own account, and
    the `User.deactivate()` invariant blocks deactivating another platform admin.
    """

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, user_id: UUID, active: bool, acting_user_id: UUID) -> bool:
        user = await self._uow.users.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundError("User not found")

        if not active and user.id == acting_user_id:
            raise InvalidOperationError("You cannot deactivate your own account")

        if user.is_active != active:
            if active:
                user.activate()
            else:
                user.deactivate()  # raises if target is a platform admin
            await self._uow.users.save(user)
            self._uow.track(user)
        return user.is_active
