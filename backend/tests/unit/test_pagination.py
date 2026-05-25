"""Unit tests for pagination."""

from __future__ import annotations

from src.application.shared.pagination import PaginatedResult, PaginationParams


def test_offset_page_1():
    p = PaginationParams(page=1, page_size=20)
    assert p.offset == 0


def test_offset_page_3():
    p = PaginationParams(page=3, page_size=20)
    assert p.offset == 40


def test_total_pages():
    r = PaginatedResult(items=[], total=95, page=1, page_size=20)
    assert r.total_pages == 5


def test_total_pages_exact():
    r = PaginatedResult(items=[], total=100, page=1, page_size=20)
    assert r.total_pages == 5


def test_total_pages_zero():
    r = PaginatedResult(items=[], total=0, page=1, page_size=20)
    assert r.total_pages == 1
