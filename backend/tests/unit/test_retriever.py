"""Unit tests for the hybrid retriever — RRF fusion logic."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from src.infrastructure.rag.retriever import HybridRetriever


def test_rrf_fuse_combines_two_lists() -> None:
    chunk_a = MagicMock()
    chunk_a.id = uuid4()
    chunk_b = MagicMock()
    chunk_b.id = uuid4()
    chunk_c = MagicMock()
    chunk_c.id = uuid4()

    list1 = [chunk_a, chunk_b]
    list2 = [chunk_b, chunk_c]

    fused = HybridRetriever._rrf_fuse(list1, list2)
    ids = [uid for uid, _ in fused]

    # chunk_b appears in both lists → should rank highest
    assert ids[0] == chunk_b.id
    assert len(fused) == 3


def test_rrf_fuse_empty_lists() -> None:
    fused = HybridRetriever._rrf_fuse([], [])
    assert fused == []


def test_rrf_fuse_single_list() -> None:
    chunk = MagicMock()
    chunk.id = uuid4()
    fused = HybridRetriever._rrf_fuse([chunk])
    assert len(fused) == 1
    assert fused[0][0] == chunk.id
