# frontdesk

Multi-tenant AI front desk that answers on its owner's behalf. Routine
questions get RAG-grounded answers from the tenant's documents; anything
the AI doesn't know is escalated to the owner as a pending question,
and the asker is notified once the owner replies.

> **Status:** v0.1.0 — 109 commits, 711 tests (531 backend + 180
> frontend), 99.4% coverage on both SonarQube dashboards (0/0/0).
> LangGraph agent loop, per-tenant LLM config, WhatsApp + Telegram
> webhooks, hybrid RAG, escalation inbox, settings dashboard,
> circuit breaker, event bus, key facts memory, Prometheus metrics.

## What it does

- **Owner side** — web dashboard with an inbox of escalated questions,
  document upload (PDF / DOCX / Markdown / plain text), and a token /
  cost ledger. The asker contact + the AI's failed answer attempt are
  shown so the owner knows exactly why an escalation happened.
- **Knowledge base** — uploaded files are chunked (~512 token windows,
  15% overlap), embedded with `text-embedding-3-large` (truncated to
  1536 dims), and indexed with pgvector HNSW + a Postgres `tsvector`
  GIN index. Retrieval is hybrid (vector + BM25) fused via Reciprocal
  Rank Fusion.
- **Escalation flow** — when the AI escalates, a `Question` row is
  created with full state-machine semantics
  (`SUBMITTED → RESOLVED | CLOSED`). The owner replies from the
  dashboard; an event will relay the reply back to the asker's channel
  once the channels phase ships.
- **Cost accountability** — every LLM call is written to a
  `token_usages` row with provider, model, tenant, thread, request ID,
  and per-segment cost in `Decimal(18, 8)`. Aggregation happens in SQL.

## Architectural highlights

- **Strict hexagonal DDD.** Domain layer has zero imports from
  application, infrastructure, drivers, or the AI layer. Application
  layer has zero infrastructure imports. LangChain lives in **one
  file** behind `LLMClientPort`.
- **DB-as-truth conversation persistence.** LangGraph orchestrates a
  single turn; the messages table is the cross-turn source of truth.
  Avoids the opaque LangGraph checkpoint blob and keeps admin UI +
  audit queries clean.
- **Tiered tool compression.** Recent tool exchanges stay verbatim
  (`tool_use` / `tool_result` blocks the LLM was trained on); older
  exchanges compress to a summary while `tool_args` + `tool_result`
  are retained in JSONB for UUID-driven recovery. Fixes the gap in
  naive "paraphrase tool result" patterns where the LLM loses
  awareness of what it previously asked.
- **Tenant isolation enforced at every query.** Routes resolve
  `tenant_id` from the authenticated user's `user_tenants` row;
  callers never get to specify it. Repositories filter at the SQL
  level. RAG retrieval includes `WHERE tenant_id = :tenant_id` in
  both the vector and BM25 stages.

## Stack

- **Backend** — Python 3.13 · FastAPI 0.128 · LangGraph 1.0 ·
  PostgreSQL 17 + pgvector 0.4 · SQLAlchemy 2.0 async · Alembic ·
  pytest with real-database integration tests
- **Frontend** — React 19 · Mantine 9 · TypeScript 6 · Vite 8 ·
  TanStack Query · React Router v7
- **Observability** — Prometheus `/metrics` endpoint · structlog ·
  request ID middleware

## Repo layout

- [backend/](backend/) — FastAPI + DDD layers
- [frontend/](frontend/) — React + Mantine owner dashboard
- [docs/](docs/) — architecture, RAG, escalation, conversations
- [CLAUDE.md](CLAUDE.md) — guidance for AI-assisted work on the repo

## Quick start

Requirements: PostgreSQL 17 with pgvector, Python 3.13 with `uv`,
Node 22+ with `npm`.

```bash
# Backend
cd backend
cp .env.example .env                    # add OPENAI_API_KEY for ingestion
uv sync --extra dev
createdb frontdesk_db && psql frontdesk_db -c 'CREATE EXTENSION vector;'
uv run alembic upgrade head
uv run uvicorn src.main:app --reload --port 8000

# Frontend (new shell)
cd frontend
cp .env.example .env
npm install
npm run dev                             # http://localhost:5173
```

## Verification

```bash
# Backend
cd backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/                        # strict, 0 errors across 217 files
uv run pytest tests/ -q                 # 531 tests, 99%+ coverage

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test                                # 180 tests, 99%+ coverage
npm run build
```

## License

MIT — see [LICENSE](LICENSE).
