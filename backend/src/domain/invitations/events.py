"""Invitation domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class InvitationCreated(DomainEvent):
    invitation_id: UUID
    tenant_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class InvitationAccepted(DomainEvent):
    invitation_id: UUID
    tenant_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class InvitationRejected(DomainEvent):
    invitation_id: UUID
    tenant_id: UUID
    email: str


@dataclass(frozen=True, kw_only=True)
class InvitationRevoked(DomainEvent):
    invitation_id: UUID
    tenant_id: UUID
    email: str
