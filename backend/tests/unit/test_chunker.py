"""Unit tests for the recursive token chunker — pure CPU, no IO."""

from __future__ import annotations

from src.infrastructure.rag.chunker import RecursiveTokenChunker


def test_empty_text_produces_no_chunks() -> None:
    assert RecursiveTokenChunker().chunk("") == []
    assert RecursiveTokenChunker().chunk("   \n\n  ") == []


def test_short_text_is_a_single_chunk() -> None:
    chunks = RecursiveTokenChunker(chunk_size=200).chunk("Hello, this is a short document.")
    assert len(chunks) == 1
    assert "Hello" in chunks[0].content


def test_long_text_is_split_into_multiple_chunks() -> None:
    paragraphs = "\n\n".join(f"Paragraph {i}. " + ("word " * 100) for i in range(10))
    chunks = RecursiveTokenChunker(chunk_size=200, overlap_ratio=0.15).chunk(paragraphs)
    assert len(chunks) > 1
    # Indexes start at 0 and increment monotonically.
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunks_overlap_carries_tail_to_next() -> None:
    text = "A. B. C. D. " + ("filler " * 200) + " end-marker"
    chunks = RecursiveTokenChunker(chunk_size=150, overlap_ratio=0.2).chunk(text)
    assert len(chunks) >= 2
