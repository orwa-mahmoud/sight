# Retrieval

Each tenant has a private document corpus. An asker's question retrieves
chunks from that tenant only — never cross-tenant. The pipeline implements
the 2026 production-RAG playbook: contextual chunking, hybrid retrieval,
Reciprocal Rank Fusion. A reranker slot is reserved for v2.

## Ingestion

```text
file (PDF/MD/DOCX/TXT)
      │
      ├─ parser (pypdf / python-docx / decode)        → plain text
      │
      ├─ RecursiveTokenChunker                        → ~512 tok chunks
      │   • split on \n\n, \n, sentence, word, char    with 15% overlap
      │   • tiktoken-sized, deterministic
      │
      ├─ OpenAIEmbedder                               → 1536-d vectors
      │   • text-embedding-3-large
      │   • dimensions=1536 (HNSW-compatible)
      │
      └─ ChunkRepository.save_many                    → chunks table
          • embedding (vector(1536))
          • content_tsvector (GENERATED from content)
          • tenant_id, document_id, chunk_index, extra_metadata
```

The `Document` aggregate moves through `uploaded -> ingesting -> ready /
failed`. If any step throws, the document is marked `failed` with the
error message; the upload metadata stays so the owner can see what
happened.

## Indexing

```sql
CREATE INDEX ix_chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX ix_chunks_content_tsvector_gin
  ON chunks USING gin (content_tsvector);
```

`content_tsvector` is a Postgres GENERATED ALWAYS column — Postgres keeps
it in sync from `content` on every write, no application-side bookkeeping.

`Vector(1536)` is the largest dimension pgvector's HNSW supports for the
default `vector` type. We get the quality of `text-embedding-3-large`
while staying HNSW-compatible by passing `dimensions=1536` to OpenAI.

## Retrieval

```text
query (string)
   │
   ▼
┌──────────────────────────────────────┐    ┌─────────────────────────┐
│ Stage 1 — vector (HNSW, cosine)      │    │ Stage 2 — BM25          │
│ • embedder.embed_query(query)        │    │ • websearch_to_tsquery  │
│ • SELECT ... ORDER BY embedding      │    │ • ts_rank ORDER BY DESC │
│           <=> :query_emb LIMIT 50    │    │ • LIMIT 50              │
│ WHERE tenant_id = :tenant_id         │    │ WHERE tenant_id = ...   │
└──────────────────┬───────────────────┘    └─────────────┬───────────┘
                   │                                      │
                   └─────────────┐    ┌───────────────────┘
                                 ▼    ▼
                          ┌──────────────────────┐
                          │ Reciprocal Rank      │
                          │ Fusion (k = 60)      │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          top_k chunks (default 8)
```

### Why hybrid?

Vector search alone misses exact-token matches: product names, acronyms,
phone numbers, place names. BM25 catches those but misses paraphrase /
semantic matches. Combining them via RRF is robust to scale differences
between scoring systems — RRF just adds reciprocal-rank contributions
from each list.

```python
score(item) = Σ over lists  1 / (k + rank_in_list(item))
```

### Why RRF and not weighted fusion?

Weighted fusion needs hand-tuned coefficients per dataset and re-tuning
when embedding models change. RRF is parameter-free except for `k`
(60 is the broadly accepted default), works across heterogeneous score
distributions, and rewards items that rank high in *both* lists more
than items that rank top in one.

## Tenant isolation

Both stages filter `tenant_id` at the SQL level. There's no API path
that retrieves cross-tenant. The agent layer (when added) takes
`tenant_id` from the resolved request scope, never from caller input.

## Future extensions (v2)

- **Cross-encoder reranker** — the `RetrievedChunk` value object already
  carries the fields a reranker needs (chunk_id, content, score). A
  reranker port + adapter (e.g. Cohere Rerank, Voyage, BGE) slots in
  between RRF and the top-k cut.
- **Per-tenant chunking config** — chunk size + overlap stored on
  `Tenant`; default falls back to the chunker's constructor.
- **Hybrid score visibility** — return separate vector + BM25 ranks in
  `RetrievedChunk` for the owner-trace UI.
- **Manual facts** — short owner-typed facts go into a `tenant_facts`
  table and get injected into the system prompt directly, bypassing
  retrieval (PropertyBot's `key_facts` pattern). v1 only does file-based
  RAG.
