"""JWT service — issues and validates access tokens.

Designed as a thin wrapper around `python-jose`. The token payload is
intentionally minimal: `sub` (user id), `tenant_id`, plus standard
`iat` / `exp` / `iss` claims. Tenant scoping is enforced by checking
`tenant_id` matches the route's path parameter where applicable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from src.domain.shared.exceptions import AuthenticationError


class JwtService:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        issuer: str = "sight",
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expire_minutes = access_token_expire_minutes
        self._issuer = issuer

    def issue_access_token(self, *, user_id: UUID, tenant_id: UUID | None = None) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id) if tenant_id else None,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._expire_minutes)).timestamp()),
            "iss": self._issuer,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm], issuer=self._issuer)
        except JWTError as exc:
            raise AuthenticationError("Invalid or expired token") from exc
