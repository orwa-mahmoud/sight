"""Invitation aggregate — a pending offer to join a tenant as a collaborator."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.domain.invitations.events import (
    InvitationAccepted,
    InvitationCreated,
    InvitationRejected,
    InvitationRevoked,
)
from src.domain.invitations.value_objects import InvitationStatus
from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.users.value_objects import UserTenantRole

_DEFAULT_TTL_DAYS = 7
_TOKEN_BYTES = 32


@dataclass(eq=False, kw_only=True)
class Invitation(BaseEntity):
    tenant_id: UUID
    email: str
    role: UserTenantRole
    token: str
    status: InvitationStatus
    invited_by_user_id: UUID
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        email: str,
        invited_by_user_id: UUID,
        role: UserTenantRole = UserTenantRole.STAFF,
        ttl_days: int = _DEFAULT_TTL_DAYS,
    ) -> Invitation:
        clean_email = email.strip().lower()
        if not clean_email:
            raise InvalidOperationError("Invitation email cannot be empty")
        now = datetime.now(UTC)
        invitation = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            email=clean_email,
            role=role,
            token=secrets.token_urlsafe(_TOKEN_BYTES),
            status=InvitationStatus.PENDING,
            invited_by_user_id=invited_by_user_id,
            expires_at=now + timedelta(days=ttl_days),
            created_at=now,
            updated_at=now,
        )
        invitation._is_new = True
        invitation._emit(InvitationCreated(invitation_id=invitation.id, tenant_id=tenant_id, email=clean_email))
        return invitation

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= self.expires_at

    def _require_pending(self) -> None:
        if self.status != InvitationStatus.PENDING:
            raise InvalidOperationError(f"Invitation is already {self.status.value}")

    def accept(self) -> None:
        self._require_pending()
        if self.is_expired():
            raise InvalidOperationError("Invitation has expired")
        self.status = InvitationStatus.ACCEPTED
        self.updated_at = datetime.now(UTC)
        self._emit(InvitationAccepted(invitation_id=self.id, tenant_id=self.tenant_id, email=self.email))

    def reject(self) -> None:
        self._require_pending()
        self.status = InvitationStatus.REJECTED
        self.updated_at = datetime.now(UTC)
        self._emit(InvitationRejected(invitation_id=self.id, tenant_id=self.tenant_id, email=self.email))

    def revoke(self) -> None:
        self._require_pending()
        self.status = InvitationStatus.REVOKED
        self.updated_at = datetime.now(UTC)
        self._emit(InvitationRevoked(invitation_id=self.id, tenant_id=self.tenant_id, email=self.email))
