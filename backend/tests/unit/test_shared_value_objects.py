"""Unit tests for shared value objects."""

from __future__ import annotations

from datetime import date

import pytest

from src.domain.shared.value_objects import DateRange, SortOrder


def test_date_range() -> None:
    r = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
    assert r.start == date(2026, 1, 1)
    assert r.end == date(2026, 12, 31)


def test_date_range_invalid() -> None:
    with pytest.raises(ValueError, match="must not be before"):
        DateRange(start=date(2026, 12, 31), end=date(2026, 1, 1))


def test_sort_order_default() -> None:
    s = SortOrder(field="created_at")
    assert s.direction == "desc"


def test_sort_order_asc() -> None:
    s = SortOrder(field="name", direction="asc")
    assert s.direction == "asc"


def test_sort_order_invalid_direction() -> None:
    with pytest.raises(ValueError, match="must be 'asc' or 'desc'"):
        SortOrder(field="name", direction="sideways")
