"""Run the RAG retrieval eval and print a report.

    uv run python -m eval.run                 # offline, no keys needed
    uv run python -m eval.run --k 3
    uv run python -m eval.run --ci            # exit non-zero if below gates

Offline backend only for now (lexical retriever over fixtures). A DB-mode backend
that drives the real HybridRetriever is on the roadmap; the metrics module is
backend-agnostic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eval.corpus import LexicalRetriever, load_corpus, overlap_fraction
from eval.metrics import aggregate, format_report, grade_item
from eval.types import GoldenItem

_HERE = Path(__file__).parent


def _load_golden(path: Path) -> list[GoldenItem]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        GoldenItem(
            id=row["id"],
            question=row["question"],
            relevant_doc_ids=row["relevant_doc_ids"],
            answer_must_include=row["answer_must_include"],
            should_escalate=row["should_escalate"],
        )
        for row in data["items"]
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="frontdesk RAG retrieval eval")
    parser.add_argument("--k", type=int, default=5, help="top-k chunks to retrieve")
    parser.add_argument(
        "--escalate-threshold",
        type=float,
        default=0.25,
        help="query/context overlap below which the agent should escalate",
    )
    parser.add_argument("--ci", action="store_true", help="exit non-zero if metrics fall below gates")
    parser.add_argument("--min-hit", type=float, default=0.9)
    parser.add_argument("--min-context", type=float, default=0.8)
    parser.add_argument("--min-escalation-recall", type=float, default=0.9)
    args = parser.parse_args(argv)

    corpus = load_corpus(_HERE / "fixtures")
    retriever = LexicalRetriever(corpus)
    golden = _load_golden(_HERE / "golden_set.json")

    outcomes = []
    for item in golden:
        ranked = retriever.search(item.question, k=args.k)
        top_overlap = overlap_fraction(item.question, ranked[0].content) if ranked else 0.0
        outcomes.append(
            grade_item(
                item,
                ranked,
                k=args.k,
                top_overlap=top_overlap,
                escalate_threshold=args.escalate_threshold,
            )
        )

    report = aggregate(outcomes, k=args.k)
    print(format_report(report))
    print(f"  corpus: {len(corpus)} docs · {len(golden)} graded questions (offline lexical backend)\n")

    if args.ci:
        failures = []
        if report.hit_at_k < args.min_hit:
            failures.append(f"hit@{args.k} {report.hit_at_k:.2%} < {args.min_hit:.0%}")
        if report.context_sufficiency < args.min_context:
            failures.append(f"context@{args.k} {report.context_sufficiency:.2%} < {args.min_context:.0%}")
        if report.escalation_recall < args.min_escalation_recall:
            failures.append(f"escalation recall {report.escalation_recall:.2%} < {args.min_escalation_recall:.0%}")
        if failures:
            print("  ❌ eval gate failed:\n   - " + "\n   - ".join(failures) + "\n")
            return 1
        print("  ✅ eval gate passed\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
