"""Invitation value objects."""

from __future__ import annotations

from enum import StrEnum


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVOKED = "revoked"
