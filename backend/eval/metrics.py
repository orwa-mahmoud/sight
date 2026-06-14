"""Grading + aggregation for the retrieval eval."""

from __future__ import annotations

from eval.types import EvalReport, GoldenItem, QuestionOutcome, ScoredDoc


def grade_item(
    item: GoldenItem,
    ranked: list[ScoredDoc],
    *,
    k: int,
    top_overlap: float,
    escalate_threshold: float,
) -> QuestionOutcome:
    topk = ranked[:k]
    ranked_doc_ids = [d.doc_id for d in topk]
    relevant = set(item.relevant_doc_ids)

    hit = False
    recall = 0.0
    reciprocal_rank = 0.0
    if relevant:
        recall = len(set(ranked_doc_ids) & relevant) / len(relevant)
        for rank, doc_id in enumerate(ranked_doc_ids, start=1):
            if doc_id in relevant:
                hit = True
                reciprocal_rank = 1.0 / rank
                break

    blob = "\n".join(d.content for d in topk).lower()
    context_sufficient = bool(item.answer_must_include) and all(kw.lower() in blob for kw in item.answer_must_include)

    predicted_escalate = (not topk) or top_overlap < escalate_threshold

    return QuestionOutcome(
        item=item,
        ranked_docs=topk,
        hit=hit,
        recall=recall,
        reciprocal_rank=reciprocal_rank,
        context_sufficient=context_sufficient,
        predicted_escalate=predicted_escalate,
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate(outcomes: list[QuestionOutcome], *, k: int) -> EvalReport:
    answerable = [o for o in outcomes if not o.item.should_escalate]
    escalate_expected = [o for o in outcomes if o.item.should_escalate]

    tp = sum(1 for o in escalate_expected if o.predicted_escalate)
    fp = sum(1 for o in answerable if o.predicted_escalate)
    fn = sum(1 for o in escalate_expected if not o.predicted_escalate)

    return EvalReport(
        k=k,
        answerable=len(answerable),
        escalation_expected=len(escalate_expected),
        hit_at_k=_mean([1.0 if o.hit else 0.0 for o in answerable]),
        recall_at_k=_mean([o.recall for o in answerable]),
        mrr=_mean([o.reciprocal_rank for o in answerable]),
        context_sufficiency=_mean([1.0 if o.context_sufficient else 0.0 for o in answerable]),
        escalation_precision=(tp / (tp + fp)) if (tp + fp) else 1.0,
        escalation_recall=(tp / (tp + fn)) if (tp + fn) else 1.0,
        outcomes=outcomes,
    )


def format_report(report: EvalReport) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append(f"  RAG retrieval eval — top-k = {report.k}")
    lines.append("  " + "─" * 64)
    lines.append(f"  {'question':<34}{'hit':>5}{'recall':>8}{'rr':>6}{'ctx':>5}{'esc':>5}")
    lines.append("  " + "─" * 64)
    for o in report.outcomes:
        esc = "↑" if o.predicted_escalate else "·"
        ctx = "✓" if o.context_sufficient else ("—" if o.item.should_escalate else "✗")
        hit = "—" if o.item.should_escalate else ("✓" if o.hit else "✗")
        lines.append(f"  {o.item.id:<34}{hit:>5}{o.recall:>8.2f}{o.reciprocal_rank:>6.2f}{ctx:>5}{esc:>5}")
    lines.append("  " + "─" * 64)
    lines.append(f"  answerable questions      : {report.answerable}")
    lines.append(f"  hit@{report.k}                    : {report.hit_at_k:.2%}")
    lines.append(f"  recall@{report.k}                 : {report.recall_at_k:.2%}")
    lines.append(f"  MRR                       : {report.mrr:.3f}")
    lines.append(f"  context sufficiency@{report.k}    : {report.context_sufficiency:.2%}")
    lines.append(f"  escalation precision      : {report.escalation_precision:.2%}")
    lines.append(f"  escalation recall         : {report.escalation_recall:.2%}")
    lines.append("")
    return "\n".join(lines)
