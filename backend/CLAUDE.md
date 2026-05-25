# frontdesk-backend -- AI assistant guidelines

## STRICT RULES

- **NEVER commit without the user explicitly saying "commit".** Not after
  fixes, not after cleanups, not after "small" changes.
- **NEVER push to remote** unless the user explicitly asks.
- **NEVER amend commits** unless the user explicitly asks.
- **NEVER manually set revision IDs in Alembic migrations.** Always use
  `uv run alembic revision --autogenerate -m "description"`.
- **Always run all checks before considering a task done:**
  1. `uv run ruff check src/ tests/`
  2. `uv run ruff format --check src/ tests/`
  3. `uv run mypy src/`
  4. `uv run pytest tests/ --tb=short -q`

## Project overview

Multi-tenant AI front desk. Stack: Python 3.13, FastAPI, LangGraph,
PostgreSQL 17 + pgvector (HNSW + GIN), SQLAlchemy 2.0 (async), Alembic.
Strict hexagonal DDD.

**Full architecture reference:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
-- layer boundaries, bounded contexts, entity patterns, CQRS, RAG pipeline,
AI orchestration, forbidden imports, testing strategy, and adding a feature.

## Commands

```bash
uv run uvicorn src.main:app --reload --port 8000   # dev server
uv run pytest                                       # tests
uv run ruff check src/ tests/                       # lint
uv run ruff format src/ tests/                      # format
uv run mypy src/                                    # strict type check
uv run alembic revision --autogenerate -m "msg"     # new migration
uv run alembic upgrade head                         # apply migrations
```

## Forbidden imports (verify)

```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" src/application/
# Should be empty.

grep -rn "^from langchain\|^from langgraph" src/domain/ src/application/
# Should be empty.
```

## Things to NEVER do

- Never import `langchain_*` or `langgraph` into `domain/`, `application/`,
  or the `ai/` layer (except `infrastructure/ai/graph.py` which is the
  single langgraph import site).
- Never hand-edit a migration to add table-creation logic -- generate it,
  then add only what autogenerate misses (e.g. `CREATE EXTENSION`, pgvector
  imports).
- Never raise `HTTPException` in a use case -- use domain exceptions from
  `domain/shared/exceptions.py` and let `drivers/api/responses.py` map them.
- Never trust client-provided `tenant_id` -- resolve from authenticated
  context or the webhook URL parameter.
- Never commit secrets -- use `.env` and `.env.example`.
- Never import concrete infrastructure classes in `application/` use cases.
- Never use `data: dict` in commands or queries -- all fields must be
  explicitly typed.
- Never commit without running the checks above.
