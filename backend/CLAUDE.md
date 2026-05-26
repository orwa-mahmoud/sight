# Frontdesk Backend — AI Assistant Guidelines

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

## Project Overview

**Frontdesk** is a multi-tenant AI front desk assistant. Stack: Python 3.13, FastAPI, LangGraph, PostgreSQL 17 + pgvector (HNSW + GIN), SQLAlchemy 2.0 (async), Alembic. Strict hexagonal DDD + CQRS. The AI agent handles visitor questions via WhatsApp, Telegram, and a direct Chat API, backed by a RAG knowledge base per tenant.

Architecture and reference docs:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) -- layer boundaries, DDD patterns, CQRS, UoW, forbidden imports, concurrency/idempotency, testing strategy, adding a feature guide.
- [`docs/RAG_PIPELINE.md`](docs/RAG_PIPELINE.md) -- document ingestion (parse/chunk/embed/persist), hybrid retrieval (vector HNSW + BM25 + RRF), tenant isolation, domain ports.
- [`docs/AI_ORCHESTRATION.md`](docs/AI_ORCHESTRATION.md) -- gateway, agent loop, LangGraph isolation, tool definitions, system prompt, context loading, tiered compression, checkpoint summarization, concurrency.
- [`docs/CHANNEL_INTEGRATION.md`](docs/CHANNEL_INTEGRATION.md) -- channel adapters (WhatsApp, Telegram, API), webhook endpoints, contact resolution, notification routing.
- [`docs/BUSINESS_OVERVIEW.md`](docs/BUSINESS_OVERVIEW.md) -- what frontdesk does, user flows, core features.
- [`docs/ERD.md`](docs/ERD.md) -- entity relationship diagram, table overview, constraints.
- [`docs/SETUP.md`](docs/SETUP.md) -- prerequisites, database creation, env vars, migrations, dev server, running tests.

## Architecture

```text
  drivers/          ->  application/  ->  domain/  <-  infrastructure/
  (primary adapters)    (use cases)      (pure)       (secondary adapters)
  +-- api/ (FastAPI)                                  +-- persistence/ (PostgreSQL)
  +-- webhooks/                                       +-- channels/ (WhatsApp, Telegram)
                                                      +-- llm/ (LangChain client)
  ai/               ->  application/  ->  domain/     +-- rag/ (Chunker, Embedder, Retriever)
  (orchestration)
  +-- gateway.py     Entry point: chat_with_agent()
  +-- agents/        LLM -> tool -> LLM loop
  +-- context/       History, memory, prompts, checkpoint
  +-- tools/         search_documents, escalate_question, save/remove_key_fact

  infrastructure/ai/graph.py  <-- ONLY langgraph import site
  bootstrap/                  <-- composition root, wires DI container
```

**Dependency direction:** inward only. Drivers -> Application -> Domain <- Infrastructure. Domain is pure (no IO). The `ai/` layer calls application use cases (never repos or ORM).

## Quick Reference

| Concept | Location |
| ------- | -------- |
| Base classes | `domain/shared/` (entities.py, events.py, exceptions.py, utils.py) |
| Domain exceptions | `domain/shared/exceptions.py` (shared across all contexts) |
| Domain entity | `domain/{context}/entities.py` -- rich, with behavior + factories + events |
| Value objects | `domain/{context}/value_objects.py` (where applicable) |
| Repository port | `domain/{context}/repositories.py` |
| ORM models | `infrastructure/persistence/postgres/models/` (one file per model) |
| Repository impl | `infrastructure/persistence/postgres/repositories/*_repo.py` |
| Command / Query | `application/{context}/commands.py` / `queries.py` -- frozen dataclasses, typed fields |
| Use case | `application/{context}/use_cases/` (one file per use case) |
| DTOs | `application/{context}/dtos.py` |
| Unit of Work | `application/shared/unit_of_work.py` -- single UoW, all repos on one session |
| DI container | `bootstrap/container.py` |
| Event handlers | `bootstrap/event_handlers.py` |
| AI gateway | `ai/gateway.py` -- single entry point: `chat_with_agent()` |
| LangGraph graph | `infrastructure/ai/graph.py` -- the ONLY langgraph import site |
| Channel adapters | `infrastructure/channels/` (WhatsApp, Telegram, API, base) |
| Error -> HTTP map | `drivers/api/responses.py` -- `domain_error_handler` |

## Bounded Contexts

| Context | Responsibility |
| ------- | -------------- |
| `auth` | Authentication, credential verification, JWT tokens, password hashing |
| `tenants` | Multi-tenancy, tenant lifecycle (create, suspend, activate, rename) |
| `tenant_config` | Per-tenant config (LLM provider/model/key, embedding config, channel creds) |
| `users` | User accounts, tenant memberships (`user_tenants`), owner registration |
| `contacts` | External people who interact with the front desk (channel senders -> entities) |
| `conversations` | Chat threads (`Conversation`) + messages (`Message`), tiered tool compression |
| `documents` | Knowledge base uploads, status machine (uploaded -> ingesting -> ready/failed) |
| `questions` | Escalated questions state machine (submitted -> resolved/closed), owner reply |
| `key_facts` | Remembered facts about contacts (preferences, context from past chats) |
| `llm_usage` | Token usage tracking per-call with Decimal(18,8) cost, domain-side pricing |
| `llm` | LLM domain port (`LLMClientPort`) + framework-agnostic value objects |
| `rag` | RAG domain ports (ChunkerPort, EmbeddingPort, RetrieverPort) + value objects |
| `telegram` | Telegram phone lookup table (telegram_user_id -> phone for contact resolution) |

**Naming:** Plural for domain concepts (`tenants`, `users`, `contacts`). Singular for capabilities (`auth`, `llm`, `rag`, `telegram`).

## File Structure

```text
src/
+-- domain/{context}/       # entities.py, repositories.py, ports.py, events.py
|   +-- shared/             # BaseEntity, DomainEvent, DomainError hierarchy
+-- application/{context}/  # commands.py, queries.py, dtos.py, use_cases/
|   +-- shared/             # UnitOfWork, event collection, pagination
+-- ai/                     # gateway.py, agents/, context/, tools/, utils/
+-- drivers/api/            # v1/{context}/, webhooks/, dependencies.py, responses.py
+-- infrastructure/
|   +-- ai/graph.py         # ONLY langgraph import site
|   +-- persistence/postgres/models/ + repositories/
|   +-- channels/, llm/, rag/, auth/, metrics/, notifications/
+-- bootstrap/              # container.py, events.py, event_handlers.py
+-- config/                 # settings.py

tests/
+-- unit/                   # domain, application, ai -- no IO; mock ports/repos
+-- integration/            # infrastructure -- real PostgreSQL (frontdesk_test DB)
```

## Domain Entity Pattern

Entities are **rich** -- behavior methods, invariant guards, event emission. No anemic data holders.

```python
@dataclass(eq=False, kw_only=True)
class Tenant(BaseEntity):
    name: str
    slug: str
    status: TenantStatus

    @classmethod
    def create(cls, *, name: str, slug: str) -> Tenant:
        now = datetime.now(UTC)
        tenant = cls(id=uuid4(), name=name.strip(), slug=slug.strip().lower(), ...)
        tenant._is_new = True
        tenant._emit(TenantCreated(tenant_id=tenant.id, name=tenant.name, slug=tenant.slug))
        return tenant

    def suspend(self) -> None:
        if self.status == TenantStatus.SUSPENDED:
            raise InvalidOperationError("Tenant is already suspended")
        ...
```

**Rules:**
- `kw_only=True` on all entity dataclasses (avoids ordering gymnastics with parent defaults)
- Factory classmethod generates UUID, sets defaults, emits `Created` event. Factory names match domain verb: `Tenant.create()`, `Conversation.start()`, `Document.upload()`, `Question.submit()`, `TokenUsage.record()`
- `is_new` / `mark_persisted()` lets repos detect insert vs update
- Events collected via `_emit()`. Use cases drain `pending_events` after commit, dispatch via event bus, then `clear_events()`
- All events inherit `DomainEvent` base (provides `event_id` + `occurred_at`)

## Domain Exceptions

All in `domain/shared/exceptions.py` (shared, not per-context):

| Exception | HTTP | When |
| --------- | ---- | ---- |
| `DomainError` | 400 | Base class |
| `EntityNotFoundError` | 404 | Entity does not exist |
| `AlreadyExistsError` | 400 | Uniqueness violation |
| `AuthenticationError` | 401 | Bad credentials, expired tokens |
| `AuthorizationError` | 403 | Insufficient permissions |
| `InvalidOperationError` | 400 | Business rule violation |

`drivers/api/responses.py` maps `DomainError` -> HTTP. Use cases raise domain exceptions -- **never** `HTTPException`.

## CQRS

**Commands and queries** are frozen dataclasses with typed fields. Never `data: dict`.

```python
@dataclass(frozen=True, kw_only=True)
class ReplyToQuestion:
    tenant_id: UUID
    question_id: UUID
    replied_by_user_id: UUID
    reply: str
```

**Rules:**
- `@dataclass(frozen=True, kw_only=True)` -- immutable parameter DTOs
- All fields **explicitly typed** -- never `data: dict`
- Use **domain-level field names** (not API names)
- API-to-domain name transforms happen at the **route layer**
- Use cases accept commands/queries, return DTOs. Domain entities never leak to API.
- One file per use case in `application/{context}/use_cases/`

## Unit of Work

Single `UnitOfWork` (`application/shared/unit_of_work.py`) wrapping one `AsyncSession` with all repos as typed attributes. Each route handler opens one session, creates a UoW, commits on success, rolls back on error.

- `uow.commit()` -- persist and commit
- `uow.flush()` -- push without commit (use between insert + FK-referencing insert in same txn)
- `uow.rollback()` -- undo on error

## Repository save() Pattern

Repos expose `save(entity)` -- insert if `is_new`, update otherwise. Domain controls creation via factory; repos just persist.

```python
# In a use case:
entity = Entity.create(...)        # domain factory
await uow.repo.save(entity)       # repo decides insert/update via is_new
await uow.commit()
```

**`get_or_create_by_phone`:** Contact repo uses `INSERT ON CONFLICT` for `(tenant_id, phone)` uniqueness. Critical for webhook idempotency.

## Contact Model

Contacts are external people who interact with a tenant's front desk. Identity + tenant scope (no lead management -- simpler than PropertyBot's Client).

**How channel contacts become real entities:**

1. **WhatsApp:** `resolve_sender()` -> `get_or_create_by_phone(tenant_id, phone)`. Phone is the natural key from Meta webhook.
2. **Telegram:** Two-step via `telegram_phones` table. Lookup `telegram_user_id` -> phone. If found, `get_or_create_by_phone` + `contact.link_telegram()`. If no phone, return `None` (contact cannot be created until user shares phone).
3. **API / Web:** Treats sender identifier as phone-like key, same `get_or_create_by_phone` flow.

Contact resolution happens **before** any message is saved, so every message has a real `participant_id` (or `None` for unresolved Telegram users).

## AI Orchestration

### Gateway -> Agent -> Tools

```text
Webhook/API -> chat_with_agent(ChatInput, uow):
    1. Load tenant config (per-tenant LLM + embedding creds from DB)
    2. Resolve sender -> Contact entity
    3. Save inbound USER message via SaveThreadMessageUseCase
    4. Load history from DB (source of truth) + key facts context
    5. Build system prompt + tool definitions
    6. Run LangGraph agent (infrastructure/ai/graph.py)
       call_llm -> tool_calls? -> execute_tools -> call_llm -> ... -> END
       Max 5 iterations safety cap
    7. Save tool exchanges + assistant reply
    8. Record token usage with domain-side cost calc
    9. Maybe create checkpoint if token budget exceeded (3000 tokens since last)
   10. Return ChatResult -> channel adapter sends reply
```

### LangGraph Isolation

`infrastructure/ai/graph.py` is the ONLY file importing `langgraph` and `langchain_core.messages`. It translates between domain `LLMMessage` and LangChain message types at the boundary. The rest of `ai/` never sees LangGraph or LangChain types.

### Available Tools

| Tool | Purpose |
| ---- | ------- |
| `search_documents` | RAG retrieval from tenant's knowledge base |
| `escalate_question` | Escalate a question the AI cannot answer to the owner |
| `save_key_fact` | Remember a fact about the current contact |
| `remove_key_fact` | Forget a previously saved fact |

Tools are framework-agnostic `ToolDef` objects (name, description, JSON Schema params). Agent tools **must call use cases, never repos or ORM directly**.

## Forbidden Imports

| Layer | Cannot import from |
| ----- | ------------------ |
| `domain/` | `application/`, `infrastructure/`, `drivers/`, `ai/`, `config/` |
| `application/` | `infrastructure/`, `drivers/`, `ai/` |
| `infrastructure/` | `drivers/`, `application/`, `ai/` |
| `ai/` | `infrastructure/` (except `infrastructure/metrics` and `infrastructure/ai/graph`), `drivers/` |

**Application layer must never:** import `HTTPException`, import concrete infrastructure classes, raise `ValueError` for business errors.

**AI layer explicit imports:** `ai/` -> `application/` (use cases), `ai/` -> `domain/` (value objects, ports, exceptions), `ai/` -> `infrastructure/metrics` (pragmatic exception). Agent tools must call use cases, never repos or ORM.

**Verify with:**

```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" src/application/
# Should be empty.

grep -rn "^from langchain\|^from langgraph" src/domain/ src/application/
# Should be empty.
```

## Commands Reference

```bash
uv run uvicorn src.main:app --reload --port 8000   # dev server
uv run pytest                                       # all tests
uv run pytest tests/ --tb=short -q                  # all tests (compact)
uv run pytest tests/unit/                            # unit tests only
uv run pytest -m integration --tb=short -q            # integration tests (real PostgreSQL)
uv run pytest path/to/test.py::TestClass::test       # single test
uv run ruff check src/ tests/                        # lint
uv run ruff format src/ tests/                       # format
uv run ruff format --check src/ tests/               # format check (CI)
uv run mypy src/                                     # strict type check
uv run alembic revision --autogenerate -m "msg"      # new migration
uv run alembic upgrade head                          # apply migrations
```

## Coding Conventions

- `async` for all I/O-bound operations
- Type hints on all functions
- Ruff for lint and format (line-length 120)
- Mypy for strict type checking
- `Readonly` / `frozen` immutability wherever possible
- Tenant access resolved from authenticated context or webhook URL -- never from client payload

## Things to NEVER Do

- Never import `langchain_*` or `langgraph` into `domain/`, `application/`, or the `ai/` layer (except `infrastructure/ai/graph.py` which is the single import site)
- Never hand-edit a migration to add table-creation logic -- generate it, then add only what autogenerate misses (e.g. `CREATE EXTENSION`, pgvector imports)
- Never raise `HTTPException` in a use case -- use domain exceptions from `domain/shared/exceptions.py`
- Never trust client-provided `tenant_id` -- resolve from authenticated context or webhook URL
- Never import concrete infrastructure classes in `application/` use cases
- Never use `data: dict` in commands or queries -- all fields explicitly typed
- Never commit secrets -- use `.env` and `.env.example`
- Never commit without running the checks above
