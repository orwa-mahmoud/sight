"""Unit tests for the search_documents tool."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF, run_search_documents
from src.domain.rag.value_objects import RetrievedChunk


def test_search_documents_def():
    assert SEARCH_DOCUMENTS_DEF.name == "search_documents"
    assert "query" in SEARCH_DOCUMENTS_DEF.parameters_schema["required"]


@pytest.mark.asyncio
async def test_run_search_empty_query():
    result = await run_search_documents(
        arguments={"query": ""},
        tenant_id=uuid4(),
        retriever=AsyncMock(),
    )
    assert result == []


@pytest.mark.asyncio
async def test_run_search_with_results():
    mock_retriever = AsyncMock()

    mock_retriever.hybrid_retrieve = AsyncMock(
        return_value=[
            RetrievedChunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                tenant_id=uuid4(),
                content="Office hours: 9-5",
                score=0.95,
                extra_metadata={},
            ),
        ]
    )
    result = await run_search_documents(
        arguments={"query": "office hours"},
        tenant_id=uuid4(),
        retriever=mock_retriever,
    )
    assert len(result) == 1
    assert "Office hours" in result[0]["content"]
    assert result[0]["score"] == 0.95
