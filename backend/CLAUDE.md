# frontdesk-backend — AI assistant guidelines

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

Multi-tenant AI front desk. Stack:

- Python 3.13 · FastAPI · LangGraph
- PostgreSQL 17 + pgvector (HNSW + GIN)
- SQLAlchemy 2.0 (async) + Alembic
- Strict hexagonal DDD

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

## Architecture (hexagonal + DDD)

```text
  drivers/        →  application/  →  domain/  ←  infrastructure/
  (entry points)     (use cases)     (pure)      (adapters)
  ├── api/                                       ├── persistence/
  └── webhooks/                                  ├── llm/
                                                 ├── rag/
                                                 └── auth/
  ai/             →  application/  →  domain/
  (orchestration)
```

**Dependency direction: inward only.** Domain is pure (no IO). Bootstrap
wires it all at startup. The `ai/` layer (when added) is cross-cutting —
it may import from `application` and `domain`, but never from `drivers`
or (except for `infrastructure/metrics`) `infrastructure`.

## File structure

```text
src/
├── ai/                            # AI orchestration (cross-cutting, planned)
├── application/                   # Use case orchestration
│   ├── auth/                      # register, authenticate, get_user
│   ├── conversations/             # save_thread_message, load_thread_history
│   ├── documents/                 # ingest, list, delete, retrieve_for_query
│   ├── llm_usage/                 # record, aggregate
│   ├── questions/                 # submit, reply, close, list
│   └── shared/                    # UnitOfWork
├── bootstrap/                     # Container, wiring
├── config/                        # Settings (pydantic-settings)
├── domain/                        # Pure business logic (no I/O)
│   ├── auth/                      # PasswordHasher port
│   ├── conversations/             # Conversation, Message
│   ├── documents/                 # Document, Chunk
│   ├── llm/                       # LLMClientPort, LLMMessage, LLMCallResult
│   ├── llm_usage/                 # TokenUsage entity, pricing
│   ├── questions/                 # Question state machine
│   ├── rag/                       # ChunkerPort, EmbeddingPort, RetrieverPort
│   ├── shared/                    # BaseEntity, DomainEvent, exceptions
│   ├── tenants/                   # Tenant aggregate
│   └── users/                     # User, UserTenant
├── drivers/                       # Entry points (FastAPI)
│   └── api/
│       ├── dependencies.py        # get_current_user, get_uow
│       ├── responses.py           # DomainError -> HTTP handler
│       └── v1/                    # versioned routes
└── infrastructure/                # Concrete adapters
    ├── auth/                      # BcryptPasswordHasher, JwtService
    ├── llm/                       # LangChainLLMClient (the ONLY langchain import site)
    ├── persistence/postgres/      # ORM models + repositories
    └── rag/                       # OpenAIEmbedder, RecursiveTokenChunker, HybridRetriever
```

## Forbidden imports

| Layer | Cannot import from |
|---|---|
| `domain/` | `application/`, `infrastructure/`, `drivers/`, `ai/`, `config/` |
| `application/` | `infrastructure/`, `drivers/`, `ai/` |
| `infrastructure/` | `drivers/`, `application/`, `ai/` |
| `ai/` | `infrastructure/` (except `infrastructure/metrics`), `drivers/` |

LangChain and LangGraph imports are confined to `infrastructure/llm/`,
`infrastructure/rag/`, and (when added) `infrastructure/ai/`. The `ai/`
agent layer may import `langchain_core.messages` types only.

Verify with:

```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" src/application/
# Should be empty.

grep -rn "^from langchain\|^from langgraph" src/domain/ src/application/
# Should be empty.
```

## Domain entity pattern

Entities are rich (behavior + invariants + event emission), not anemic data
holders. Use `kw_only=True` dataclasses so subclasses can declare required
fields without ordering gymnastics.

```python
@dataclass(eq=False, kw_only=True)
class Tenant(BaseEntity):
    name: str
    slug: str
    status: TenantStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, name: str, slug: str) -> Tenant:
        tenant = cls(id=uuid4(), name=name.strip(), slug=slug.lower(), ...)
        tenant._is_new = True
        tenant._emit(TenantCreated(...))
        return tenant

    def suspend(self) -> None:
        if self.status == TenantStatus.SUSPENDED:
            raise InvalidOperationError("Already suspended")
        ...
```

## Unit of Work

Each route opens one session via `get_uow`, commits on success, rolls back
on error. Use cases interact ONLY with the UoW — never the session
directly. Use `uow.flush()` between an insert and an FK-referencing
insert in the same transaction.

## Commands & queries

Frozen `kw_only` dataclasses, typed fields only — never `data: dict`:

```python
@dataclass(frozen=True, kw_only=True)
class ReplyToQuestion:
    tenant_id: UUID
    question_id: UUID
    replied_by_user_id: UUID
    reply: str
```

## Domain exceptions

All in `src/domain/shared/exceptions.py`. Use cases raise these, never
`HTTPException`. The mapping happens in `drivers/api/responses.py`.

| Exception | HTTP | When |
|---|---|---|
| `EntityNotFoundError` | 404 | Entity does not exist |
| `AlreadyExistsError` | 400 | Uniqueness violation |
| `AuthenticationError` | 401 | Bad credentials / missing token |
| `AuthorizationError` | 403 | Insufficient permissions / cross-tenant |
| `InvalidOperationError` | 400 | Business rule rejected |

## Do / Don't

- **Do** use entity `create()` factories for new aggregates
- **Do** raise domain exceptions, never `HTTPException`
- **Do** filter by `tenant_id` in every multi-tenant query
- **Do** keep `__table_args__` for HNSW + GIN indexes on `chunks`
- **Don't** import infrastructure adapters in application use cases
- **Don't** put LangChain types in domain, application, or `ai/` signatures
- **Don't** trust client-provided `tenant_id` — resolve from `user_tenants`
- **Don't** add new dependencies without checking pyproject.toml
- **Don't** commit secrets — use `.env` and `.env.example`
