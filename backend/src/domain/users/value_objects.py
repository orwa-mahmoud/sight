"""User value objects."""

from __future__ import annotations

from enum import StrEnum


class UserTenantRole(StrEnum):
    """Role of a user within a tenant.

    `OWNER` is the only role in v1; `STAFF` reserved for future team support.
    """

    OWNER = "owner"
    STAFF = "staff"
