"""Unit tests for domain exceptions."""

from __future__ import annotations

from src.domain.shared.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    DomainError,
    EntityNotFoundError,
    InvalidOperationError,
)


def test_exception_http_status_codes() -> None:
    assert DomainError.http_status == 400
    assert EntityNotFoundError.http_status == 404
    assert AlreadyExistsError.http_status == 400
    assert AuthenticationError.http_status == 401
    assert AuthorizationError.http_status == 403
    assert InvalidOperationError.http_status == 400


def test_domain_error_is_exception() -> None:
    assert issubclass(DomainError, Exception)
    assert issubclass(EntityNotFoundError, DomainError)
