"""OpenAI embeddings adapter — implements `EmbeddingPort`.

Client creation is deferred to the first actual embedding call so that
constructing an embedder with an empty API key (e.g. before the tenant
has configured one) doesn't crash the route.
"""

from __future__ import annotations

from collections.abc import Sequence

from openai import AsyncOpenAI

from src.domain.shared.exceptions import InvalidOperationError


class OpenAIEmbedder:
    """Implements `EmbeddingPort` using OpenAI's embeddings endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        dimensions: int,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._api_key:
                raise InvalidOperationError("Embedding API key not configured. Set it in Settings → Embedding.")
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    _BATCH_SIZE = 512

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        cleaned = [t if t.strip() else " " for t in texts]
        all_embeddings: list[list[float]] = []
        for i in range(0, len(cleaned), self._BATCH_SIZE):
            batch = cleaned[i : i + self._BATCH_SIZE]
            response = await client.embeddings.create(
                model=self._model,
                input=list(batch),
                dimensions=self._dimensions,
            )
            all_embeddings.extend(d.embedding for d in response.data)
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed_documents([text])
        return result[0] if result else []

    @property
    def dimensions(self) -> int:
        return self._dimensions
