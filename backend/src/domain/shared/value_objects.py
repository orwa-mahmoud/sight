"""Shared value objects used across bounded contexts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class DateRange:
    """Inclusive date range for filtering queries."""

    start: str  # ISO format date
    end: str  # ISO format date


@dataclass(frozen=True, kw_only=True)
class SortOrder:
    field: str
    direction: str = "desc"  # asc or desc
