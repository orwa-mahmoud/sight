"""AcceptInvitation — a logged-in user (matching the invited email) joins."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError
from src.domain.users.entities import UserTenant
from src.domain.users.value_objects import UserTenantRole


class AcceptInvitation:
    """Accept a pending invite. The caller's email must match the invite."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, token: str, accepting_user_id: UUID) -> UUID:
        invitation = await self._uow.invitations.get_by_token(token)
        if invitation is None:
            raise EntityNotFoundError("Invitation not found")

        user = await self._uow.users.get_by_id(accepting_user_id)
        if user is None:
            raise EntityNotFoundError("User not found")
        if user.email != invitation.email:
            raise AuthorizationError("This invitation was sent to a different email address")

        invitation.accept()  # raises if not pending or expired

        # Idempotent membership: only add the link if not already present.
        existing = await self._uow.user_tenants.get(user.id, invitation.tenant_id)
        if existing is None:
            link = UserTenant.create(
                user_id=user.id,
                tenant_id=invitation.tenant_id,
                role=UserTenantRole.STAFF,
            )
            await self._uow.user_tenants.save(link)
            self._uow.track(link)

        await self._uow.invitations.save(invitation)
        self._uow.track(invitation)
        return invitation.tenant_id
