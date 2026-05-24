"""Auth-related domain ports.

Concrete implementations (bcrypt, argon2, etc.) live in `infrastructure/auth/`.
Use cases depend on this port so the algorithm is swappable and so plaintext
passwords never reach the domain entities.
"""

from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    """Hash and verify passwords without exposing the algorithm to callers."""

    def hash(self, plaintext: str) -> str: ...

    def verify(self, plaintext: str, hashed: str) -> bool: ...
