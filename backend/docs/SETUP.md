# Frontdesk Backend — Setup Guide

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
createdb frontdesk_db

# Test database (for integration tests)
createdb frontdesk_test
```

### Enable pgvector

```bash
psql frontdesk_db -c 'CREATE EXTENSION IF NOT EXISTS vector;'
psql frontdesk_test -c 'CREATE EXTENSION IF NOT EXISTS vector;'
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
| `DATABASE_URL` | Yes | Async connection string: `postgresql+asyncpg://user:pass@localhost:5432/frontdesk_db` |
| `DATABASE_URL_SYNC` | Yes | Sync connection string (for Alembic): `postgresql://user:pass@localhost:5432/frontdesk_db` |
| `DATABASE_URL_TEST` | Yes | Test database: `postgresql+asyncpg://user:pass@localhost:5432/frontdesk_test` |
| `REDIS_URL` | Yes | Redis connection: `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Yes | Random 256-bit string for JWT signing |
| `OPENAI_API_KEY` | For RAG | Required if using OpenAI for embeddings/LLM |
| `ANTHROPIC_API_KEY` | Optional | For Anthropic (Claude) LLM provider |
| `GOOGLE_API_KEY` | Optional | For Google Gemini LLM provider |

Per-tenant LLM and embedding credentials are stored in the `tenant_configs` table. The env vars above serve as defaults for tenants without custom config.

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

---

## 6. Running Tests

```bash
# All tests (unit + integration)
uv run pytest tests/ --tb=short -q

# Unit tests only (no database required)
uv run pytest tests/unit/

# Integration tests only (requires frontdesk_test database)
uv run pytest -m integration --tb=short -q

# Single test file or test
uv run pytest tests/path/to/test_file.py
uv run pytest tests/path/to/test_file.py::TestClass::test_method
```

Integration tests run against a real PostgreSQL database (`frontdesk_test`). The test fixtures handle table creation and cleanup.

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
