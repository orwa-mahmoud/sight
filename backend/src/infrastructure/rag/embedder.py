"""OpenAI embeddings adapter — implements `EmbeddingPort`.

Client creation is deferred to the first actual embedding call so that
constructing an embedder with an empty API key (e.g. before the tenant
has configured one) doesn't crash the route.
"""

from __future__ import annotations

from collections.abc import Sequence

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    _BATCH_SIZE = 512

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        cleaned = [t if t.strip() else " " for t in texts]
        all_embeddings: list[list[float]] = []
        for i in range(0, len(cleaned), self._BATCH_SIZE):
            all_embeddings.extend(await self._embed_batch(list(cleaned[i : i + self._BATCH_SIZE])))
        if len(all_embeddings) != len(cleaned):
            raise InvalidOperationError(
                f"Embedding provider returned {len(all_embeddings)} vectors for {len(cleaned)} chunks."
            )
        return all_embeddings

    @retry(
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=1, max=20),
        reraise=True,
    )
    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """Embed one batch, retrying transient provider errors — especially 429 rate
        limits — so a momentary TPM spike during bulk ingestion (many/large documents
        at once) doesn't fail the whole document. Up to 6 attempts with exponential
        backoff rides out a per-minute token window."""
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=batch,
            dimensions=self._dimensions,
        )
        # The API may not return items in request order — sort by index so each
        # embedding lines up with its source chunk.
        ordered = sorted(response.data, key=lambda d: d.index)
        return [d.embedding for d in ordered]

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed_documents([text])
        return result[0] if result else []

    @property
    def dimensions(self) -> int:
        return self._dimensions
