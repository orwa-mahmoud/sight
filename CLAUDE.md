# frontdesk — AI assistant guidelines

## Repo layout

- [backend/](backend/) — FastAPI + LangGraph, strict hexagonal DDD.
  Architecture: [backend/docs/ARCHITECTURE.md](backend/docs/ARCHITECTURE.md).
  Rules: [backend/CLAUDE.md](backend/CLAUDE.md).
- [frontend/](frontend/) — React 19 + Mantine 9 owner dashboard.
  Architecture: [frontend/docs/ARCHITECTURE.md](frontend/docs/ARCHITECTURE.md).
  Rules: [frontend/CLAUDE.md](frontend/CLAUDE.md).

Read the subproject's CLAUDE.md before doing work inside it.

## Working across both projects

1. Land the backend change first so the API contract is stable.
2. Backend uses snake_case in JSON; frontend types follow the same shape.
3. Run each project's checks before declaring done.

## CI checks (must pass before any commit)

Backend:
```bash
cd backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest --tb=short -q --cov=src
```

Frontend:
```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

DDD layer audit (must return empty):
```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" backend/src/application/
grep -rn "^from langchain\|^from langgraph" backend/src/domain/ backend/src/application/
```

## Conventions

- **Commits**: conventional-commit format. Body explains the *why*.
- **Migrations**: `uv run alembic revision --autogenerate -m "..."` — never hand-written.
- **Secrets**: never commit. `.env.example` is the contract.
- **Docs**: if a doc disagrees with the code, the code wins — update the doc in the same change.

## Things to NEVER do

- Never commit `langchain_*` or `langgraph` imports into `domain/` or `application/`.
- Never hand-edit a migration to add table-creation logic.
- Never raise `HTTPException` in a use case — use domain exceptions.
- Never trust client-provided `tenant_id` — resolve from `user_tenants`.
- Never commit without running the CI checks above.
