"""Retrieval-quality eval harness for the RAG knowledge base.

Offline by default: it scores a golden Q&A set against a lexical retriever over
the fixture corpus, with NO database or API keys required — so it runs in CI and
on any laptop. The same metrics module plugs into the real `HybridRetriever`
(DB mode) once you have a populated tenant and embedding keys.

Run: `uv run python -m eval.run`  (or `make eval` from the repo root)
"""
