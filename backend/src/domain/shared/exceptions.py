"""Domain exception hierarchy.

Use cases raise these instead of `HTTPException`. A driver-layer error handler
maps them to HTTP responses. This keeps the application + domain layers free
of any web-framework dependency.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors. Maps to HTTP 400 by default.

    `message` is the English text (also the developer-facing detail). An
    optional `code` lets the API boundary translate the message for non-English
    `Accept-Language` requests; English always uses `message`, so a missing code
    or catalog entry simply yields the original English string.
    """

    http_status: int = 400

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class EntityNotFoundError(DomainError):
    """A referenced aggregate does not exist."""

    http_status = 404


class AlreadyExistsError(DomainError):
    """Uniqueness invariant violated (e.g. duplicate email, duplicate slug)."""

    http_status = 400


class AuthenticationError(DomainError):
    """Credentials missing or invalid."""

    http_status = 401


class AuthorizationError(DomainError):
    """Caller lacks permission for the requested action."""

    http_status = 403


class InvalidOperationError(DomainError):
    """A business rule rejected this transition (e.g. closing an already-closed ticket)."""

    http_status = 400
