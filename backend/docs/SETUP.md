# Sight Backend — Setup Guide

## Prerequisites

| Tool | Version | Purpose |
| ---- | ------- | ------- |
| Python | 3.13+ | Runtime |
| uv | latest | Package manager (replaces pip/venv) |
| PostgreSQL | 17+ | Primary database |
| pgvector | 0.4+ | Vector similarity search extension |
| Redis | 7+ | Thread locking, rate limiting |

---

## 1. Clone and Install

```bash
cd backend
uv sync --extra dev
```

This creates a `.venv` and installs all dependencies including dev/test extras.

---

## 2. Database Setup

### Create the databases

```bash
# Main database
createdb sight_db

# Test database (for integration tests)
createdb sight_test
```

### Enable pgvector

```bash
psql sight_db -c 'CREATE EXTENSION IF NOT EXISTS vector;'
psql sight_test -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

The `vector` extension is required for the RAG embedding columns (HNSW index on `vector(1536)`).

---

## 3. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `DATABASE_URL` | Yes | Async connection string: `postgresql+asyncpg://user:pass@localhost:5432/sight_db` |
| `DATABASE_URL_SYNC` | Yes | Sync connection string (for Alembic): `postgresql://user:pass@localhost:5432/sight_db` |
| `DATABASE_URL_TEST` | Yes | Test database: `postgresql+asyncpg://user:pass@localhost:5432/sight_test` |
| `REDIS_URL` | Yes | Redis connection: `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Yes | Random 256-bit string for JWT signing |
| `ENCRYPTION_KEY` | Prod | Fernet key for encrypting tenant secrets at rest. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

All LLM, embedding, and channel credentials are strictly per-tenant via the `tenant_configs` table. There are no global API key env vars.

---

## 4. Run Migrations

```bash
uv run alembic upgrade head
```

This creates all tables, indexes (HNSW, GIN, B-tree), and constraints.

---

## 5. Start the Dev Server

```bash
uv run uvicorn src.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Start the ingestion worker

Document ingestion (parse/chunk/embed) runs on an **Arq worker**, not in the web
request, so you also need the worker running for uploads to be processed — without
it, uploaded documents stay `uploaded` and never become `ready`. In a second shell:

```bash
uv run arq src.drivers.jobs.worker.WorkerSettings
```

It connects to the same Redis (`REDIS_URL`) and reads uploaded files from
`UPLOAD_STORAGE_DIR` (default `var/uploads`), so the web and worker must share that
directory. The worker also re-enqueues any document stuck mid-ingest on a restart.
(The Docker setup runs this `worker` service for you.)

---

## 6. Running Tests

```bash
# All tests (unit + integration)
uv run pytest tests/ --tb=short -q

# Unit tests only (no database required)
uv run pytest tests/unit/

# Integration tests only (requires sight_test database)
uv run pytest -m integration --tb=short -q

# Single test file or test
uv run pytest tests/path/to/test_file.py
uv run pytest tests/path/to/test_file.py::TestClass::test_method
```

Integration tests run against a real PostgreSQL database (`sight_test`). The test fixtures handle table creation and cleanup.

---

## 7. Verification Commands

Run all of these before considering any task done:

```bash
uv run ruff check src/ tests/          # Lint
uv run ruff format --check src/ tests/  # Format check
uv run mypy src/                        # Type check (strict)
uv run pytest tests/ --tb=short -q      # All tests
```

---

## 8. Creating Migrations

Always use autogenerate — never write migration files by hand:

```bash
uv run alembic revision --autogenerate -m "add widget table"
uv run alembic upgrade head
```

If autogenerate misses something (e.g. `CREATE EXTENSION`, pgvector imports), add it manually to the generated file — but never set revision IDs by hand.

---

## 9. Per-Tenant Configuration

After creating a tenant and user via the registration API (`POST /api/v1/auth/register`), configure the tenant's LLM and channel settings via the Settings page in the frontend dashboard, or directly via the API:

- `PUT /api/v1/settings/llm` — LLM provider, model, API key, temperature, max tokens
- `PUT /api/v1/settings/embedding` — Embedding provider, model, API key, dimensions
- `PUT /api/v1/settings/whatsapp` — WhatsApp Cloud API credentials
- `PUT /api/v1/settings/telegram` — Telegram Bot API token
- `PUT /api/v1/settings/bot` — Bot name, welcome message, language

### Channel Webhook Registration

**WhatsApp:** In Meta Business Manager, set the webhook URL to:
```
https://your-domain/webhooks/{tenant_id}/whatsapp
```

**Telegram:** Call the Telegram `setWebhook` API:
```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain/webhooks/{tenant_id}/telegram
```

---

## 10. Troubleshooting

Common first-run failures and their fixes.

**`type "vector" does not exist` (or other pgvector errors).** The extension isn't
enabled on that database. Enable it once per database — the Docker image does this
automatically, local installs don't:
```bash
psql sight_db   -c 'CREATE EXTENSION IF NOT EXISTS vector;'
psql sight_test -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

**`alembic upgrade` fails, or the schema looks wrong.** Confirm the database exists
and `DATABASE_URL_SYNC` points at it, then re-run `uv run alembic upgrade head`. On a
throwaway dev DB the fastest reset is to drop and recreate:
```bash
dropdb sight_db && createdb sight_db
psql sight_db -c 'CREATE EXTENSION vector;'
uv run alembic upgrade head
```

**`connection refused` / `could not connect to server`.** PostgreSQL isn't running,
or `DATABASE_URL` / `DATABASE_URL_SYNC` point at the wrong host/port. Check it's up
with `pg_isready` and that the port matches (default `5432`).

**`address already in use`.** Something else holds the port — `8000` (API), `5173`
(Vite), or `5432` (Postgres). Stop the other process, or change the port
(`uvicorn … --port 8001`, `npm run dev -- --port 5174`).

**Uploaded documents stay `uploaded` and never reach `ready`.** The ingestion worker
isn't running — start it alongside the API (see
[Start the ingestion worker](#start-the-ingestion-worker)).

**Docker: stale data or a broken first boot.** Reset the containers *and* volumes,
then rebuild from scratch:
```bash
docker compose down -v
docker compose up --build
```
