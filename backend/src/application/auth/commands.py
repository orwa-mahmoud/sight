"""Auth commands — frozen dataclasses passed to use cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class RegisterOwner:
    email: str
    password: str
    full_name: str | None
    tenant_name: str
    tenant_slug: str


@dataclass(frozen=True, kw_only=True)
class AuthenticateUser:
    email: str
    password: str
