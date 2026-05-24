"""Recursive character chunker — implements `ChunkerPort`.

Splits on the longest available separator (paragraph -> line -> sentence ->
word -> char) so the resulting chunks respect natural boundaries. Targets
~512 tokens with ~15% overlap (per the 2026 production-RAG playbook).
Uses tiktoken to size in tokens rather than characters.
"""

from __future__ import annotations

import tiktoken

from src.domain.rag.value_objects import TextChunk

_DEFAULT_TOKENS_PER_CHUNK = 512
_DEFAULT_OVERLAP_RATIO = 0.15
_SEPARATORS = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", "")


class RecursiveTokenChunker:
    """Implements `ChunkerPort`. Token-aware, recursive, deterministic."""

    def __init__(
        self,
        *,
        chunk_size: int = _DEFAULT_TOKENS_PER_CHUNK,
        overlap_ratio: float = _DEFAULT_OVERLAP_RATIO,
        encoding_name: str = "o200k_base",
    ) -> None:
        self._chunk_size = chunk_size
        self._overlap = max(1, int(chunk_size * overlap_ratio))
        self._encoding = tiktoken.get_encoding(encoding_name)

    def chunk(self, text: str) -> list[TextChunk]:
        text = text.strip()
        if not text:
            return []

        pieces = self._recursive_split(text, _SEPARATORS)
        # Merge small pieces up to chunk_size with overlap.
        merged = self._merge_with_overlap(pieces)
        return [TextChunk(index=i, content=p) for i, p in enumerate(merged) if p.strip()]

    # ── Recursive splitter ────────────────────────────────────────
    def _recursive_split(self, text: str, separators: tuple[str, ...]) -> list[str]:
        if self._token_len(text) <= self._chunk_size:
            return [text]
        if not separators:
            # Hard split on tokens.
            return self._token_chunks(text)
        sep, rest = separators[0], separators[1:]
        if sep == "":
            return self._token_chunks(text)
        parts = text.split(sep)
        out: list[str] = []
        for p in parts:
            piece = p if sep == "" else p + sep
            if self._token_len(piece) <= self._chunk_size:
                out.append(piece)
            else:
                out.extend(self._recursive_split(piece, rest))
        return out

    def _token_chunks(self, text: str) -> list[str]:
        tokens = self._encoding.encode(text)
        return [
            self._encoding.decode(tokens[i : i + self._chunk_size]) for i in range(0, len(tokens), self._chunk_size)
        ]

    def _merge_with_overlap(self, pieces: list[str]) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for piece in pieces:
            piece_tokens = self._token_len(piece)
            if current and current_tokens + piece_tokens > self._chunk_size:
                chunks.append("".join(current))
                # Build overlap tail from the end of the just-flushed chunk.
                tail_tokens = self._encoding.encode("".join(current))[-self._overlap :]
                current = [self._encoding.decode(tail_tokens)] if tail_tokens else []
                current_tokens = len(tail_tokens)
            current.append(piece)
            current_tokens += piece_tokens

        if current:
            chunks.append("".join(current))
        return chunks

    def _token_len(self, text: str) -> int:
        return len(self._encoding.encode(text))
