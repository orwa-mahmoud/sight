"""Bcrypt-backed `PasswordHasher` implementation.

Bcrypt is configured with a work factor of 12 — a balance between security
and worst-case authentication latency on small/medium hardware in 2026.
"""

from __future__ import annotations

import bcrypt


class BcryptPasswordHasher:
    """Implements the `PasswordHasher` port using bcrypt."""

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, plaintext: str) -> str:
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")

    def verify(self, plaintext: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            # Malformed hash — never matches.
            return False
