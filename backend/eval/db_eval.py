"""DB-mode RAG eval — grade the REAL retriever, not the offline lexical stand-in.

`eval.run` scores an offline lexical retriever so it can run anywhere. This runs
the *production* pipeline — pgvector HNSW + Postgres BM25 + RRF + the LLM reranker
— against a tenant whose documents are already ingested, so you can measure what
the reranker and Contextual Retrieval actually buy you.

Point it at an ingested tenant and supply keys:

    DATABASE_URL=postgresql+asyncpg://... \\
    EVAL_EMBEDDING_API_KEY=sk-... EVAL_LLM_API_KEY=sk-... \\
    EVAL_TENANT_ID=<uuid> \\
    uv run python -m eval.db_eval

Edit `golden_set.json` so `relevant_doc_ids` are that tenant's document filenames.
Without the keys/tenant it prints how to enable it and exits 0.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from eval.corpus import overlap_fraction
from eval.metrics import aggregate, format_report, grade_item
from eval.run import load_golden
from eval.types import QuestionOutcome, ScoredDoc
from src.infrastructure.llm.client import LangChainLLMClient
from src.infrastructure.persistence.postgres.database import async_session_factory
from src.infrastructure.persistence.postgres.models.document import DocumentModel
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.reranker import LLMReranker
from src.infrastructure.rag.retriever import HybridRetriever

_HERE = Path(__file__).parent
_TOP_K = 8
_ESCALATE_THRESHOLD = 0.25
_EMBEDDING_MODEL = "text-embedding-3-large"
_RERANK_MODEL = "gpt-4o-mini"


async def _run(*, embedding_key: str, llm_key: str, tenant_id: UUID) -> None:
    golden = load_golden(_HERE / "golden_set.json")
    embedder = OpenAIEmbedder(api_key=embedding_key, model=_EMBEDDING_MODEL, dimensions=1536)
    llm = LangChainLLMClient(provider="openai", model=_RERANK_MODEL, api_key=llm_key)

    async with async_session_factory() as session:
        rows = (
            await session.execute(
                select(DocumentModel.id, DocumentModel.filename).where(DocumentModel.tenant_id == tenant_id)
            )
        ).all()
        id_to_name: dict[UUID, str] = {row.id: row.filename for row in rows}

        retriever = HybridRetriever(session=session, embedder=embedder, reranker=LLMReranker(llm))
        outcomes: list[QuestionOutcome] = []
        for item in golden:
            chunks = await retriever.hybrid_retrieve(query=item.question, tenant_id=tenant_id, top_k=_TOP_K)
            ranked = [
                ScoredDoc(doc_id=id_to_name.get(c.document_id, str(c.document_id)), score=c.score, content=c.content)
                for c in chunks
            ]
            top_overlap = overlap_fraction(item.question, ranked[0].content) if ranked else 0.0
            outcomes.append(
                grade_item(item, ranked, k=_TOP_K, top_overlap=top_overlap, escalate_threshold=_ESCALATE_THRESHOLD)
            )

    await embedder.close()
    print(format_report(aggregate(outcomes, k=_TOP_K)))
    print(f"  DB mode: real HybridRetriever (vector + BM25 + RRF + LLM rerank) over tenant {tenant_id}\n")


def main() -> None:
    embedding_key = os.environ.get("EVAL_EMBEDDING_API_KEY", "")
    llm_key = os.environ.get("EVAL_LLM_API_KEY", "")
    tenant_raw = os.environ.get("EVAL_TENANT_ID", "")
    if not (embedding_key and llm_key and tenant_raw):
        print(
            "DB-mode eval needs EVAL_EMBEDDING_API_KEY, EVAL_LLM_API_KEY, and EVAL_TENANT_ID "
            "(a tenant whose documents are already ingested), plus DATABASE_URL. "
            "See eval/README.md.",
            file=sys.stderr,
        )
        return
    asyncio.run(_run(embedding_key=embedding_key, llm_key=llm_key, tenant_id=UUID(tenant_raw)))


if __name__ == "__main__":
    main()
