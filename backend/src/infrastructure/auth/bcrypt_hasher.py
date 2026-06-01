"""Bcrypt-backed `PasswordHasher` implementation.

Bcrypt is configured with a work factor of 12 — a balance between security
and worst-case authentication latency on small/medium hardware in 2026.

Passwords are SHA-256 pre-hashed (then base64-encoded) before bcrypt. Bcrypt
silently truncates inputs beyond 72 bytes; pre-hashing collapses any-length
password into a fixed 44-byte value so the full password always contributes to
the result (and avoids the well-known truncation/null-byte pitfalls).
"""

from __future__ import annotations

import base64
import hashlib

import bcrypt


def _prehash(plaintext: str) -> bytes:
    """SHA-256 the password and base64-encode it to a fixed 44-byte value."""
    digest = hashlib.sha256(plaintext.encode("utf-8")).digest()
    return base64.b64encode(digest)


class BcryptPasswordHasher:
    """Implements the `PasswordHasher` port using bcrypt."""

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, plaintext: str) -> str:
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(_prehash(plaintext), salt).decode("utf-8")

    def verify(self, plaintext: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(_prehash(plaintext), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            # Malformed hash — never matches.
            return False
