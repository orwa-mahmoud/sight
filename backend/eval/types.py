"""Typed records shared across the eval harness."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class GoldenItem:
    """One graded question. Empty relevant_doc_ids + should_escalate => not in KB."""

    id: str
    question: str
    relevant_doc_ids: list[str]
    answer_must_include: list[str]
    should_escalate: bool


@dataclass(frozen=True, kw_only=True)
class ScoredDoc:
    """A document ranked by the retriever (best chunk per document)."""

    doc_id: str
    score: float
    content: str


@dataclass(frozen=True, kw_only=True)
class QuestionOutcome:
    """Per-question grading result."""

    item: GoldenItem
    ranked_docs: list[ScoredDoc]
    hit: bool  # any relevant doc in top-k (answerable items only)
    recall: float  # fraction of relevant docs in top-k
    reciprocal_rank: float  # 1/rank of first relevant doc, else 0
    context_sufficient: bool  # top-k context contains all answer keywords
    predicted_escalate: bool  # retriever found no confident context


@dataclass(frozen=True, kw_only=True)
class EvalReport:
    """Aggregate metrics over the whole golden set."""

    k: int
    answerable: int
    escalation_expected: int
    hit_at_k: float
    recall_at_k: float
    mrr: float
    context_sufficiency: float
    escalation_precision: float
    escalation_recall: float
    outcomes: list[QuestionOutcome]
