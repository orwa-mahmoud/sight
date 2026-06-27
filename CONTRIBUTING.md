# Contributing to Sight

Thank you for your interest in contributing. This guide covers how to get the
project running locally, where to make changes, and what we expect in pull
requests.

## Start here

| I want to… | Go to |
|------------|-------|
| Run the app quickly | [README — Quick start](README.md#quick-start) (Docker recommended) |
| Understand the backend design | [backend/docs/ARCHITECTURE.md](backend/docs/ARCHITECTURE.md) |
| Understand the frontend design | [frontend/docs/ARCHITECTURE.md](frontend/docs/ARCHITECTURE.md) |
| Add a backend feature | [Adding a feature](backend/docs/ARCHITECTURE.md#adding-a-feature) in the architecture doc |
| Report a bug or request a feature | [Open an issue](https://github.com/orwa-mahmoud/sight/issues/new/choose) |

Read the subproject guidelines before editing code inside them:

- [backend/CLAUDE.md](backend/CLAUDE.md) — layer rules, checks, conventions
- [frontend/CLAUDE.md](frontend/CLAUDE.md) — feature modules, i18n, DataTable

## Development setup

### Docker (recommended)

```bash
cp .env.docker.example .env.docker
# Set JWT_SECRET_KEY and ENCRYPTION_KEY (see comments in the file).
docker compose up --build
# Frontend: http://localhost:3000   API: http://localhost:8000
```

Migrations run on backend startup. No manual DB setup required.

### Local (without Docker)

**Backend** — PostgreSQL 17 with pgvector, Python 3.13, `uv`:

```bash
cd backend
cp .env.example .env
uv sync --extra dev
createdb sight_db && psql sight_db -c 'CREATE EXTENSION vector;'
uv run alembic upgrade head
uv run uvicorn src.main:app --reload --port 8000
```

**Frontend** — Node 22+:

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Full environment details: [backend/docs/SETUP.md](backend/docs/SETUP.md).

## Running checks

Run the relevant project's checks before opening a PR. CI runs the same gates on
every pull request to `main`.

### Backend

```bash
cd backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --tb=short -q
```

Integration tests need a local `sight_test` database (see
[backend/docs/SETUP.md](backend/docs/SETUP.md)):

```bash
uv run pytest -m integration --tb=short -q
```

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Where to make changes

### Backend

Hexagonal DDD + CQRS. Dependency direction is **inward only**:

```text
drivers/  →  application/  →  domain/  ←  infrastructure/
ai/       →  application/  →  domain/
```

| Change type | Location |
|-------------|----------|
| Business rules | `backend/src/domain/{context}/` |
| Use cases | `backend/src/application/{context}/use_cases/` |
| API routes | `backend/src/drivers/api/v1/{context}/` |
| DB / channels / RAG | `backend/src/infrastructure/` |
| AI agent / tools | `backend/src/ai/` (tools call use cases, never repos) |
| LangGraph | `backend/src/infrastructure/ai/graph.py` only |

**Never:**

- Import `langchain_*` or `langgraph` into `domain/` or `application/`
- Raise `HTTPException` in a use case — use domain exceptions
- Trust client-provided `tenant_id` — resolve from auth or webhook context
- Hand-write Alembic migrations — use `uv run alembic revision --autogenerate -m "..."`

Step-by-step guide: [backend/docs/ARCHITECTURE.md § Adding a Feature](backend/docs/ARCHITECTURE.md#adding-a-feature).

### Frontend

Feature-based modules under `frontend/src/features/`. Each feature owns its
`api.ts`, `types.ts`, and page components.

| Change type | Location |
|-------------|----------|
| New page / feature | `frontend/src/features/{name}/` |
| Shared UI | `frontend/src/shared/components/` |
| Auth | `frontend/src/auth/` |
| Routing | `frontend/src/app/router.tsx` |
| API client | `frontend/src/core/api/client.ts` |

**Rules:**

- Backend JSON is `snake_case` — mirror it in `types.ts` (no codegen)
- Add UI strings to **both** `en` and `ar` locale files
- Use path aliases across modules (`@features/*`, `@shared/*`, …)
- No cross-feature imports

Land **backend changes first** when a feature spans both projects, so the API
contract is stable before updating the frontend.

## Pull requests

1. **Branch** from `main` — `feat/…`, `fix/…`, `chore/…`, etc.
2. **Scope** — one logical change per PR. Smaller PRs review faster.
3. **Tests** — add or update tests for behavior you change. Bug fixes should
   include a regression test when practical.
4. **Docs** — if code and docs disagree, update the doc in the same PR.
5. **Commits** — [conventional commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `chore:`, …). The body should explain *why*, not just what.
6. **Checks** — all CI jobs must pass before merge.

Describe in the PR:

- What problem it solves
- How you tested it
- Any breaking API or config changes

## Good first issues

These are well-scoped starter tasks. Pick one, comment on the issue (or open a
PR referencing it), and ask if anything is unclear.

| Area | Task | Hints |
|------|------|-------|
| Frontend | Per-user tenant switcher UI | Backend resolves first membership today; needs API + shell work |
| Backend | Email delivery for invitation links | `create_invitation` returns a token; wire SMTP or a provider port |
| Frontend | More locale coverage audit | Find hardcoded strings; add `en` + `ar` keys |
| Backend | Additional channel adapter (e.g. Slack) | Follow `infrastructure/channels/` + webhook pattern |
| Frontend | DataTable bulk actions on Documents page | `DataTable` supports bulk actions; wire delete |
| Backend | Webhook retry / dead-letter logging | See `infrastructure/channels/` retry helpers |
| Docs | Improve setup troubleshooting section | `backend/docs/SETUP.md` — common Docker/DB errors |
| Tests | Increase integration coverage for admin routes | `tests/integration/test_admin_api.py` patterns |

Want to propose a new good-first issue? Open a feature request and suggest the
`good first issue` label.

## Questions

Open a [GitHub issue](https://github.com/orwa-mahmoud/sight/issues/new/choose)
for bugs, feature ideas, or questions. For security vulnerabilities, please
report privately to the repository owner rather than opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
