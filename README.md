# Sight

[![CI](https://github.com/orwa-mahmoud/sight/actions/workflows/ci.yml/badge.svg)](https://github.com/orwa-mahmoud/sight/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)
![React 19](https://img.shields.io/badge/React-19-61dafb.svg)
![PostgreSQL 17 + pgvector](https://img.shields.io/badge/PostgreSQL-17%20%2B%20pgvector-336791.svg)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Multi-tenant AI front desk that answers on your behalf. Tenants upload
their knowledge base, connect WhatsApp and Telegram, and the AI handles
incoming questions — grounded in the tenant's own documents. Anything the
AI can't answer gets routed to the owner's inbox for a human reply.

_Live demo: coming soon_ &nbsp;·&nbsp; [Demo](#demo) &nbsp;·&nbsp; [Quick start](#quick-start) &nbsp;·&nbsp; [Architecture](backend/docs/ARCHITECTURE.md) &nbsp;·&nbsp; [Contributing](CONTRIBUTING.md)

## Demo

[![Watch the demo — ask anything about Westeros, get a grounded, cited answer](docs/screenshots/library-poster.png)](https://orwa-mahmoud.github.io/sight/demo/#library)

Point Sight at a library and ask anything — it answers grounded in the source
material and **cites the exact book** every time. Here it's reading the full
_A Song of Ice and Fire_ saga (~5,000 pages). _Click to play (0:44)._

### Built for real front desks

The same engine pointed at a business's own knowledge base — a bank's support desk
answering from its policy documents, and escalating to a human when it can't:

| Owner inbox (escalation) | Knowledge base | AI answering, with sources |
|---|---|---|
| ![Owner inbox with an escalated question](docs/screenshots/dashboard.png) | ![Knowledge base of uploaded documents](docs/screenshots/documents.png) | ![AI answering a question and citing the source document](docs/screenshots/chat.png) |

▶ **[Watch the front-desk walkthrough](https://orwa-mahmoud.github.io/sight/demo/#frontdesk)** — a support desk answering from its own documents, with a live human escalation.

## Features

- **RAG-grounded answers** — hybrid retrieval (vector + BM25 + RRF) over each
  tenant's own documents; the AI cites their knowledge base, not the open web.
- **Human-in-the-loop escalation** — anything the AI can't answer lands in the
  owner's inbox with the AI's attempt for context; the reply relays back.
- **Omnichannel** — WhatsApp Cloud API, Telegram, and a built-in chat/dashboard,
  all behind one agent gateway.
- **Multi-tenant by design** — strict per-tenant isolation at the app layer plus
  Postgres Row-Level Security; per-tenant LLM provider/model/keys.
- **Per-contact memory + cost accounting** — the agent remembers key facts across
  conversations and tracks token spend per tenant.
- **Bilingual UI** — English + Arabic with full RTL, light/dark mode.

## Start here

| | |
|---|---|
| **Run it** | [Quick start](#quick-start) — Docker one-liner below |
| **Contribute** | [CONTRIBUTING.md](CONTRIBUTING.md) — setup, checks, PR guide, good first issues |
| **Backend design** | [backend/docs/ARCHITECTURE.md](backend/docs/ARCHITECTURE.md) — DDD layers, bounded contexts, adding a feature |
| **Frontend design** | [frontend/docs/ARCHITECTURE.md](frontend/docs/ARCHITECTURE.md) — features, auth, DataTable, i18n |
| **Data model** | [backend/docs/ERD.md](backend/docs/ERD.md) |
| **Report a bug / request a feature** | [Open an issue](https://github.com/orwa-mahmoud/sight/issues/new/choose) |

## Architecture

```mermaid
flowchart TB
    subgraph channels [Channels]
        WA[WhatsApp]
        TG[Telegram]
        API[Chat API / Dashboard]
    end

    subgraph drivers [Drivers — entry points]
        WH[Webhooks]
        REST[FastAPI /api/v1]
    end

    subgraph ai [AI orchestration]
        GW[gateway.chat_with_agent]
        AG[Agent loop — LangGraph]
        TOOLS[Tools: search · escalate · key facts]
    end

    subgraph core [Application + Domain]
        UC[Use cases — CQRS]
        DOM[Rich entities + events]
    end

    subgraph infra [Infrastructure]
        PG[(PostgreSQL + pgvector + RLS)]
        RAG[Hybrid RAG — vector + BM25]
        LLM[Per-tenant LLM client]
        CH[Channel adapters]
    end

    subgraph ui [Frontend]
        SPA[React SPA — Mantine + TanStack Query]
    end

    WA --> WH
    TG --> WH
    API --> WH
    API --> REST
    WH --> GW
    REST --> UC
    REST --> SPA
    SPA --> REST
    GW --> AG
    AG --> TOOLS
    TOOLS --> UC
    GW --> UC
    UC --> DOM
    UC --> PG
    TOOLS --> RAG
    AG --> LLM
    GW --> CH
```

**Dependency direction (backend):** drivers → application → domain ←
infrastructure. The `ai/` layer orchestrates by calling use cases — never
repositories or ORM directly. LangGraph is isolated to a single file:
`backend/src/infrastructure/ai/graph.py`.

Deeper dives: [backend architecture](backend/docs/ARCHITECTURE.md) ·
[RAG pipeline](backend/docs/RAG_PIPELINE.md) ·
[AI orchestration](backend/docs/AI_ORCHESTRATION.md) ·
[channel integration](backend/docs/CHANNEL_INTEGRATION.md) ·
[frontend architecture](frontend/docs/ARCHITECTURE.md).

## How it works

1. **Owner registers** and creates a tenant.
2. **Uploads documents** (PDF, DOCX, Markdown, plain text) — chunked,
   embedded, and indexed for hybrid retrieval.
3. **Connects channels** — WhatsApp and Telegram via the settings dashboard.
4. **Contacts message** through any connected channel.
5. **AI answers** using RAG over the tenant's documents.
6. **Unanswered questions** land in the owner's inbox with the AI's
   attempted answer for context.
7. **Owner replies** from the dashboard — the response relays back
   through the original channel.

The AI remembers key facts about each contact across conversations and
tracks token usage per tenant with full cost accountability.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.13 · FastAPI · LangGraph · PostgreSQL 17 + pgvector |
| Frontend | React 19 · Mantine 9 · TypeScript · Vite · TanStack Query · i18n (EN/AR + RTL) |
| AI | Hybrid RAG (vector + BM25 + RRF) · per-turn LangGraph orchestration |
| Channels | WhatsApp Cloud API · Telegram Bot API |
| Observability | Prometheus metrics · structlog · request ID tracing |

## Quick start

### Docker (recommended)

Requires Docker + Docker Compose. Brings up Postgres (with pgvector), Redis,
the backend, the ingestion worker, and the frontend.

```bash
cp .env.docker.example .env.docker
# Edit .env.docker: set JWT_SECRET_KEY and ENCRYPTION_KEY (commands are in the file).
docker compose up --build
# Frontend: http://localhost:3000   API: http://localhost:8000
```

The backend container applies database migrations on startup, so the schema —
**including the pgvector extension**, which the first migration enables via
`CREATE EXTENSION IF NOT EXISTS vector` — is ready on first boot with no manual
step. The frontend is served by nginx, which reverse-proxies `/api` and
`/webhooks` to the backend, so the app talks to the API over the same origin
(no CORS, and the auth cookie stays first-party).

Then open http://localhost:3000 and register an owner account. To use document
ingestion and chat, add an LLM + embedding API key under **Settings** — keys are
per-tenant (stored in the database), so the RAG features light up once one is saved.

### Local (without Docker)

Requires PostgreSQL 17 with pgvector, Python 3.13 with `uv`, Node 22+.

```bash
# Backend
cd backend
cp .env.example .env
uv sync --extra dev
createdb sight_db && psql sight_db -c 'CREATE EXTENSION vector;'
uv run alembic upgrade head
uv run uvicorn src.main:app --reload --port 8000

# Ingestion worker (second shell, same dir) — processes uploaded documents.
# Without it, uploads stay "uploaded" and never become "ready".
uv run arq src.drivers.jobs.worker.WorkerSettings

# Frontend
cd frontend
npm install
npm run dev    # http://localhost:5173 (Vite proxies /api + /webhooks to :8000)
```

**Stuck on first run?** See [Troubleshooting](backend/docs/SETUP.md#10-troubleshooting) for common fixes — pgvector, migrations, ports, the ingestion worker, and Docker resets.

## Frontend highlights

- **Bilingual UI (English + Arabic) with full RTL** — language switcher in the
  app shell, self-hosted Arabic font, layout mirrors via Mantine's
  `DirectionProvider`. Backend API error messages localize via `Accept-Language`.
- **Light / dark mode** toggle.
- **Unified DataTable** — `@adapttable/mantine` via a thin app facade (`@shared/components/datatable`): sort, search, filter drawer + chips, paged & infinite modes, responsive desktop/mobile, URL-synced state, row actions with confirm modals, EN/AR labels, and mount animations.
- **Route-level code splitting**, path aliases, typed config, Prettier + strict
  TypeScript/ESLint.

## Notes & current limitations

- **Authentication is cookie-based.** Login/register set an httpOnly
  `sight_token` cookie (the SPA never stores the JWT in JS, so it is not
  exposed to XSS). The API also accepts a `Bearer` token for programmatic
  clients (curl, scripts, the test suite).
- **One tenant per user (v1).** A user is currently resolved to their first
  tenant membership. Multi-tenant *data isolation* is fully enforced
  server-side, but a per-user tenant switcher is not built yet.
- **`/auth/refresh` is a sliding-session re-issue**, not a separate
  refresh-token grant: it mints a fresh access token for the already
  authenticated user. The `JWT_REFRESH_TOKEN_EXPIRE_DAYS` setting is reserved
  for a future refresh-token flow.

## Documentation

| Doc | What it covers |
|-----|---------------|
| [Contributing](CONTRIBUTING.md) | Dev setup, checks, where to change code, PR expectations, good first issues |
| [Backend architecture](backend/docs/ARCHITECTURE.md) | DDD layers, bounded contexts, entity patterns, CQRS |
| [RAG pipeline](backend/docs/RAG_PIPELINE.md) | Chunking, embedding, hybrid retrieval |
| [AI orchestration](backend/docs/AI_ORCHESTRATION.md) | Agent loop, tools, LangGraph, prompt design |
| [Channel integration](backend/docs/CHANNEL_INTEGRATION.md) | WhatsApp/Telegram adapters, contact resolution |
| [Data model](backend/docs/ERD.md) | Entity relationship diagram |
| [Setup guide](backend/docs/SETUP.md) | Full environment setup |
| [Frontend architecture](frontend/docs/ARCHITECTURE.md) | Components, state management, routing |
| [Design system](frontend/docs/DESIGN_SYSTEM.md) | Theme, colors, component patterns |

## Contributing

Contributions are welcome — bugs, features, docs, and tests. See
[CONTRIBUTING.md](CONTRIBUTING.md) for local setup, which checks to run, and
[good first issues](CONTRIBUTING.md#good-first-issues) if you're looking for a
place to start.

## License

This project is licensed under the [MIT License](LICENSE).
