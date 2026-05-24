"""Tenant domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class TenantCreated(DomainEvent):
    tenant_id: UUID
    name: str
    slug: str


@dataclass(frozen=True, kw_only=True)
class TenantSuspended(DomainEvent):
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class TenantActivated(DomainEvent):
    tenant_id: UUID
