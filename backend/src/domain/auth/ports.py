"""Auth-related domain ports.

Concrete implementations (bcrypt, argon2, etc.) live in `infrastructure/auth/`.
Use cases depend on this port so the algorithm is swappable and so plaintext
passwords never reach the domain entities.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class PasswordHasher(Protocol):
    """Hash and verify passwords without exposing the algorithm to callers."""

    def hash(self, plaintext: str) -> str: ...

    def verify(self, plaintext: str, hashed: str) -> bool: ...


class TokenServicePort(Protocol):
    """Issue and decode authentication tokens."""

    def issue_access_token(self, *, user_id: UUID, tenant_id: UUID | None = None) -> str: ...

    def decode(self, token: str) -> dict[str, Any]: ...
