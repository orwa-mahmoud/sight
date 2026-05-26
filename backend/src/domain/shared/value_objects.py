"""Shared value objects used across bounded contexts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, kw_only=True)
class DateRange:
    """Inclusive date range for filtering queries."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            msg = f"DateRange end ({self.end}) must not be before start ({self.start})"
            raise ValueError(msg)


@dataclass(frozen=True, kw_only=True)
class SortOrder:
    field: str
    direction: str = "desc"

    def __post_init__(self) -> None:
        if self.direction not in ("asc", "desc"):
            msg = f"SortOrder direction must be 'asc' or 'desc', got '{self.direction}'"
            raise ValueError(msg)
