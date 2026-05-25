"""Unit tests for shared value objects."""

from __future__ import annotations

from src.domain.shared.value_objects import DateRange, SortOrder


def test_date_range():
    r = DateRange(start="2026-01-01", end="2026-12-31")
    assert r.start == "2026-01-01"
    assert r.end == "2026-12-31"


def test_sort_order_default():
    s = SortOrder(field="created_at")
    assert s.direction == "desc"


def test_sort_order_asc():
    s = SortOrder(field="name", direction="asc")
    assert s.direction == "asc"
