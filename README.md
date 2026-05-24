# frontdesk

Multi-tenant AI front desk that answers on your behalf. Routine questions get grounded answers from your documents and facts; anything outside its knowledge is forwarded to you as a pending question, with the asker notified once you reply.

> **Status:** under active construction. Not deployed yet.

## What it does

- **Asker side** — reaches your AI via Telegram or WhatsApp. Gets an answer grounded in your tenant's documents and facts. If the AI doesn't know, the question is escalated and the asker is told someone will follow up.
- **Owner side** — web dashboard with an inbox of escalated questions, document upload, conversation history, and token/cost usage. Reply from the dashboard or from your own preferred channel (Telegram / WhatsApp).
- **Owner-AI chat** — talk to your own assistant for end-of-day summaries, pending question lists, and analytics over your tenant's traffic.

## Stack

- **Backend** — Python 3.13 · FastAPI · LangGraph · PostgreSQL 17 + pgvector
- **Frontend** — React 19 · Mantine 8 · TypeScript · Vite
- **Architecture** — strict hexagonal DDD. The LLM client and LangGraph orchestrator are isolated behind domain ports — the agent layer never sees `langchain_core` or `langgraph` symbols.
- **Retrieval** — hybrid (vector + BM25) over pgvector with HNSW indexing, cross-encoder reranking, contextual chunking (256-512 tokens, 15% overlap).

## Repo layout

- `backend/` — FastAPI + LangGraph backend (DDD layers)
- `frontend/` — React + Mantine owner dashboard
- `docs/` — architecture and design notes

## License

MIT — see [LICENSE](LICENSE).
