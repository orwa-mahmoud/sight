"""Question domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class QuestionSubmitted(DomainEvent):
    question_id: UUID
    tenant_id: UUID
    channel: str
    asker_contact: str | None


@dataclass(frozen=True, kw_only=True)
class QuestionResolved(DomainEvent):
    """Emitted when the owner replies. A policy subscribes to relay the
    answer back to the original asker via their channel."""

    question_id: UUID
    tenant_id: UUID
    replied_by_user_id: UUID


@dataclass(frozen=True, kw_only=True)
class QuestionClosed(DomainEvent):
    question_id: UUID
    tenant_id: UUID
