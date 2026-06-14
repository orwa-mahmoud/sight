"""Offline corpus + a small lexical retriever (no DB, no API keys).

Chunks the fixture markdown by paragraph, scores chunks by IDF-weighted term
overlap with light suffix stemming (so "weekends" matches "weekend"). This is the
default backend so the harness runs anywhere; the real `HybridRetriever`
(vector + BM25 + RRF) is the DB-mode backend with the same `Retriever` contract.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Protocol

from eval.types import ScoredDoc

_WORD_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = frozenset(
    """a an and are as at be by can do does for from get how i if in into is it its me my
    of on or our the their there to up we what when where which who you your""".split()
)


def _stem(token: str) -> str:
    """Tiny suffix normalizer — not linguistically correct, just enough to match
    common variants in a small KB (plurals / gerunds)."""
    for suffix, repl in (("ing", ""), ("ies", "y"), ("es", ""), ("s", "")):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[: len(token) - len(suffix)] + repl
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase → words (len≥2 or digits) → stemmed."""
    out: list[str] = []
    for raw in _WORD_RE.findall(text.lower()):
        if len(raw) >= 2 or raw.isdigit():
            out.append(_stem(raw))
    return out


def content_terms(text: str) -> set[str]:
    """Stemmed, stopword-free terms — used for the escalation overlap signal."""
    return {t for t in tokenize(text) if t not in _STOPWORDS}


def overlap_fraction(query: str, content: str) -> float:
    """Fraction of the query's content terms present in `content`."""
    q = content_terms(query)
    if not q:
        return 0.0
    return len(q & set(tokenize(content))) / len(q)


class Retriever(Protocol):
    """Contract shared by the offline backend and the real DB-backed retriever."""

    def search(self, query: str, *, k: int) -> list[ScoredDoc]: ...


class _Chunk:
    __slots__ = ("doc_id", "terms", "text")

    def __init__(self, doc_id: str, text: str) -> None:
        self.doc_id = doc_id
        self.text = text
        self.terms = set(tokenize(text))


def load_corpus(fixtures_dir: Path) -> dict[str, str]:
    """Map doc_id (filename) → full document text."""
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(fixtures_dir.glob("*.md"))}


class LexicalRetriever:
    """IDF-weighted, presence-based chunk retriever over the fixture corpus."""

    def __init__(self, corpus: dict[str, str]) -> None:
        self._chunks: list[_Chunk] = []
        for doc_id, text in corpus.items():
            for raw_para in re.split(r"\n\s*\n", text.strip()):
                para = raw_para.strip()
                if para:
                    self._chunks.append(_Chunk(doc_id, para))
        n = max(len(self._chunks), 1)
        df: dict[str, int] = {}
        for chunk in self._chunks:
            for term in chunk.terms:
                df[term] = df.get(term, 0) + 1
        # BM25-style IDF: always positive, rarer terms weigh more.
        self._idf = {t: math.log((n - c + 0.5) / (c + 0.5) + 1.0) for t, c in df.items()}

    def search(self, query: str, *, k: int) -> list[ScoredDoc]:
        q_terms = content_terms(query)
        scored: list[ScoredDoc] = []
        for chunk in self._chunks:
            score = sum(self._idf.get(t, 0.0) for t in q_terms if t in chunk.terms)
            if score > 0:
                scored.append(ScoredDoc(doc_id=chunk.doc_id, score=round(score, 4), content=chunk.text))
        scored.sort(key=lambda d: d.score, reverse=True)
        return scored[:k]
