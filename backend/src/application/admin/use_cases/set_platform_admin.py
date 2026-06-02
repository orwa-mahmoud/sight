"""SetPlatformAdmin — grant/revoke the platform super-admin flag by email.

Used by the CLI (`src.cli admin grant/revoke`) and the startup bootstrap
(`PLATFORM_ADMIN_EMAIL`). Not exposed as an HTTP endpoint.
"""

from __future__ import annotations

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import EntityNotFoundError


class SetPlatformAdmin:
    """Grant (granted=True) or revoke (granted=False) platform admin by email."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, email: str, granted: bool) -> bool:
        user = await self._uow.users.get_by_email(email)
        if user is None:
            raise EntityNotFoundError(f"No user with email {email!r}")

        if granted:
            user.grant_platform_admin()
        else:
            user.revoke_platform_admin()
        await self._uow.users.save(user)
        self._uow.track(user)
        return user.is_platform_admin
