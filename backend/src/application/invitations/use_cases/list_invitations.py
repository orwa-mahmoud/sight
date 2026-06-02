"""ListInvitations — all invitations for a tenant (owner view)."""

from __future__ import annotations

from uuid import UUID

from src.application.invitations.dtos import InvitationDTO
from src.application.invitations.mappers import to_invitation_dto
from src.application.shared.unit_of_work import UnitOfWork


class ListInvitations:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: UUID) -> list[InvitationDTO]:
        invitations = await self._uow.invitations.list_for_tenant(tenant_id)
        return [to_invitation_dto(inv) for inv in invitations]
