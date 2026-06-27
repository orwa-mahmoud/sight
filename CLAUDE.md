# Sight — AI assistant guidelines

## Repo Layout

| Project | Stack | Guidelines |
| ------- | ----- | ---------- |
| [backend/](backend/) | FastAPI + LangGraph, hexagonal DDD | [backend/CLAUDE.md](backend/CLAUDE.md), [backend/docs/](backend/docs/) |
| [frontend/](frontend/) | React 19 + Mantine 9, TanStack Query | [frontend/CLAUDE.md](frontend/CLAUDE.md), [frontend/docs/](frontend/docs/) |

**Read the subproject's CLAUDE.md before doing work inside it.**

## Cross-Project Workflow

1. Land the backend change first so the API contract is stable.
2. Backend uses **snake_case** in JSON; frontend types mirror the same shape (no codegen).
3. Run each project's checks before declaring done.

## Conventions

- **Commits**: conventional-commit format. Body explains the *why*.
- **Migrations**: `uv run alembic revision --autogenerate -m "..."` -- never hand-written.
- **Secrets**: never commit. `.env.example` is the contract.
- **Docs**: if a doc disagrees with the code, the code wins -- update the doc in the same change.

## Things to NEVER Do

- Never commit secrets or `.env` files.
- Never trust client-provided `tenant_id` -- resolve from authenticated context.
- Never commit `langchain_*` or `langgraph` imports into `domain/` or `application/`.
