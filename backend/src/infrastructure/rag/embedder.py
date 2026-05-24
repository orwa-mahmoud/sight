"""OpenAI embeddings adapter — implements `EmbeddingPort`.

`text-embedding-3-large` supports the `dimensions` parameter to truncate
its 3072-d native output. We default to 1536 so the resulting vectors fit
under pgvector's HNSW max-dim of 2000 while preserving most of the model's
retrieval quality.
"""

from __future__ import annotations

from collections.abc import Sequence

from openai import AsyncOpenAI

from src.config.settings import get_settings


class OpenAIEmbedder:
    """Implements `EmbeddingPort` using OpenAI's embeddings endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key or "")
        self._model = model or settings.default_embedding_model
        self._dimensions = dimensions or settings.default_embedding_dimensions

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        # Strip + dedupe-blank guard; the API rejects empty strings.
        cleaned = [t if t.strip() else " " for t in texts]
        response = await self._client.embeddings.create(
            model=self._model,
            input=list(cleaned),
            dimensions=self._dimensions,
        )
        return [d.embedding for d in response.data]

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed_documents([text])
        return result[0] if result else []

    @property
    def dimensions(self) -> int:
        return self._dimensions
