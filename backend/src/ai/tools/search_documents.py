"""search_documents tool — RAG retrieval over the tenant's corpus.

Called by the agent when it needs to ground an answer in the owner's
uploaded documents. Returns the top-k chunks with content snippets
the agent can cite in its reply.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.ai.types import ToolDef
from src.application.documents.queries import RetrieveForQuery
from src.application.documents.use_cases.retrieve_for_query import RetrieveForQueryUseCase
from src.domain.rag.ports import RetrieverPort

SEARCH_DOCUMENTS_DEF = ToolDef(
    name="search_documents",
    description=(
        "Search the owner's knowledge base for information relevant to the asker's question. "
        "Returns the most relevant document chunks. Use this before answering any factual question."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query — rephrase the asker's question for retrieval.",
            },
        },
        "required": ["query"],
    },
)


async def run_search_documents(
    *,
    arguments: dict[str, Any],
    tenant_id: UUID,
    retriever: RetrieverPort,
) -> list[dict[str, Any]]:
    query_text = arguments.get("query", "")
    if not query_text:
        return []
    use_case = RetrieveForQueryUseCase(retriever=retriever)
    chunks = await use_case.execute(RetrieveForQuery(tenant_id=tenant_id, query=query_text, top_k=8))
    return [{"content": c.content, "score": round(c.score, 4), "chunk_id": str(c.chunk_id)} for c in chunks]
