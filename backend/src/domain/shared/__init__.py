"""Shared domain primitives — BaseEntity, DomainEvent, exceptions."""

from src.domain.shared.entities import BaseEntity
from src.domain.shared.events import DomainEvent
from src.domain.shared.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    DomainError,
    EntityNotFoundError,
    InvalidOperationError,
)

__all__ = [
    "AlreadyExistsError",
    "AuthenticationError",
    "AuthorizationError",
    "BaseEntity",
    "DomainError",
    "DomainEvent",
    "EntityNotFoundError",
    "InvalidOperationError",
]
