# frontdesk

Multi-tenant AI front desk that answers on your behalf. Tenants upload
their knowledge base, connect WhatsApp and Telegram, and the AI handles
incoming questions — grounded in the tenant's own documents. Anything the
AI can't answer gets routed to the owner's inbox for a human reply.

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
| Frontend | React 19 · Mantine 9 · TypeScript · Vite · TanStack Query |
| AI | Hybrid RAG (vector + BM25 + RRF) · per-turn LangGraph orchestration |
| Channels | WhatsApp Cloud API · Telegram Bot API |
| Observability | Prometheus metrics · structlog · request ID tracing |

## Quick start

Requires PostgreSQL 17 with pgvector, Python 3.13 with `uv`, Node 22+.

```bash
# Backend
cd backend
cp .env.example .env
uv sync --extra dev
createdb frontdesk_db && psql frontdesk_db -c 'CREATE EXTENSION vector;'
uv run alembic upgrade head
uv run uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev    # http://localhost:5173
```

## Documentation

| Doc | What it covers |
|-----|---------------|
| [Backend architecture](backend/docs/ARCHITECTURE.md) | DDD layers, bounded contexts, entity patterns, CQRS |
| [RAG pipeline](backend/docs/RAG_PIPELINE.md) | Chunking, embedding, hybrid retrieval |
| [AI orchestration](backend/docs/AI_ORCHESTRATION.md) | Agent loop, tools, LangGraph, prompt design |
| [Channel integration](backend/docs/CHANNEL_INTEGRATION.md) | WhatsApp/Telegram adapters, contact resolution |
| [Data model](backend/docs/ERD.md) | Entity relationship diagram |
| [Setup guide](backend/docs/SETUP.md) | Full environment setup |
| [Frontend architecture](frontend/docs/ARCHITECTURE.md) | Components, state management, routing |
| [Design system](frontend/docs/DESIGN_SYSTEM.md) | Theme, colors, component patterns |

## License

MIT
