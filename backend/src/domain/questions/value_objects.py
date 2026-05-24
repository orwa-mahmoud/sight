"""Question value objects."""

from __future__ import annotations

from enum import StrEnum


class QuestionStatus(StrEnum):
    SUBMITTED = "submitted"  # waiting for owner
    RESOLVED = "resolved"  # owner replied
    CLOSED = "closed"  # owner closed without reply
