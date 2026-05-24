"""Unit tests for the bcrypt password hasher."""

from __future__ import annotations

from src.infrastructure.auth.bcrypt_hasher import BcryptPasswordHasher


def test_hash_and_verify() -> None:
    hasher = BcryptPasswordHasher(rounds=4)  # low rounds for speed in tests
    hashed = hasher.hash("my-secret-password")
    assert hashed != "my-secret-password"
    assert hasher.verify("my-secret-password", hashed)


def test_wrong_password_does_not_verify() -> None:
    hasher = BcryptPasswordHasher(rounds=4)
    hashed = hasher.hash("correct")
    assert not hasher.verify("wrong", hashed)


def test_malformed_hash_returns_false() -> None:
    hasher = BcryptPasswordHasher(rounds=4)
    assert not hasher.verify("anything", "not-a-bcrypt-hash")
