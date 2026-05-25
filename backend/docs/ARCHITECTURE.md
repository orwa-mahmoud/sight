# Frontdesk Backend Architecture

Hexagonal DDD + CQRS. The AI agent is a cross-cutting orchestration layer that calls application use cases. Domain is pure; infrastructure implements domain ports. References: Cosmic Python, Eric Evans, Vaughn Vernon.

## Architecture

```text
+-----------------------------------------------------------+
|                 DRIVERS (Primary Adapters)                 |
|                                                           |
|  drivers/api/v1/    FastAPI REST endpoints                |
|  drivers/api/webhooks/  WhatsApp, Telegram, Chat API      |
|                          |                                |
+---------------------------+-------------------------------+
                            v
+-----------------------------------------------------------+
|              APPLICATION + DOMAIN (Core)                   |
|                                                           |
|  application/     commands, queries, use cases, DTOs       |
|  domain/          entities, value objects, events           |
|                   repository ports, gateway ports           |
|                          |                                |
+---------------------------+-------------------------------+
                            ^
+---------------------------+-------------------------------+
|            INFRASTRUCTURE (Secondary Adapters)              |
|                                                           |
|  persistence/     PostgreSQL 17 (SQLAlchemy 2.0 async)    |
|  channels/        WhatsApp (Meta Cloud), Telegram (Bot)   |
|  llm/             LangChain multi-provider LLM client     |
|  rag/             Chunker, Embedder, Hybrid Retriever     |
|  auth/            JWT, bcrypt password hashing            |
|  notifications/   Channel-agnostic notification routing   |
+-----------------------------------------------------------+

+-----------------------------------------------------------+
|            AI (Cross-cutting Orchestration)                 |
|                                                           |
|  ai/gateway.py        Single entry point: chat_with_agent |
|  ai/agents/agent.py   LLM -> tool -> LLM loop            |
|  ai/context/          History, memory, prompts, checkpoint|
|  ai/tools/            search_documents, escalate_question,|
|                       save_key_fact, remove_key_fact       |
|                          |                                |
|  Calls application/ use cases (never repos or ORM)        |
|  LLM client injected as LLMClientPort (infra/llm/)       |
+-----------------------------------------------------------+

+-----------------------------------------------------------+
|  infrastructure/ai/graph.py                                |
|  ONLY file importing langgraph. Translates domain types   |
|  to/from LangChain messages at the boundary.              |
+-----------------------------------------------------------+

          bootstrap/  <-- wires it all together at startup
```

**Dependency direction:** inward only. Drivers -> Application -> Domain. Infrastructure implements domain ports. The `ai/` layer is cross-cutting orchestration that calls application use cases.

- **Drivers** call `application/` use cases -- they are entry points, never called by inner layers
- **AI** orchestrates by calling use cases (never repos or ORM directly). May import from `application/` and `domain/`. LLM infrastructure lives in `infrastructure/llm/` and is injected via the DI container
- **Application** orchestrates domain logic via commands/queries and use cases
- **Domain** is pure -- defines entities, business rules, and port interfaces (no IO)
- **Infrastructure** implements ports -- repos, channel adapters, LLM client, RAG pipeline
- **Bootstrap** is the composition root -- wires dependencies at startup via the DI container

All outbound dependencies (DB, notifications, LLM, embeddings) have a port interface in `domain/{context}/ports.py` or `domain/{context}/repositories.py`. Application and infrastructure meet only at runtime via bootstrap.

## Quick Reference

| Concept | Location |
| ------- | -------- |
| Base classes | `domain/shared/` (entities.py, events.py, value_objects.py) |
| Domain exceptions | `domain/shared/exceptions.py` (DomainError hierarchy -- shared across all contexts) |
| Domain entity | `domain/{context}/entities.py` -- rich entities with behavior, factories, and events |
| ORM models | `infrastructure/persistence/postgres/models/` (one file per model) |
| Value object | `domain/*/value_objects.py` |
| Repository (interface) | `domain/*/repositories.py` (ContactRepository, ConversationRepository, etc.) |
| Gateway port (interface) | `domain/*/ports.py` (LLMClientPort, EmbeddingPort, RetrieverPort, NotificationPort) |
| Repository (impl) | `infrastructure/persistence/postgres/repositories/*_repo.py` |
| Domain operations | `domain/*/operations.py` -- pure helpers that delegate to entity methods |
| Event | `domain/*/events.py` |
| Command | `application/{context}/commands.py` -- frozen dataclasses with typed fields |
| Query | `application/{context}/queries.py` -- frozen dataclasses with typed fields |
| Use case | `application/{context}/use_cases/` (one file per use case) |
| DTOs | `application/{context}/dtos.py` -- use cases accept commands/queries, return DTOs |
| UoW | `application/shared/unit_of_work.py` -- single UoW with all repos on one session |
| DI container | `bootstrap/container.py` -- builds use cases, caches singletons |
| Event handlers | `bootstrap/event_handlers.py` -- side effects on domain events |
| AI gateway | `ai/gateway.py` -- single entry point: `chat_with_agent()` |
| LangGraph graph | `infrastructure/ai/graph.py` -- the ONLY langgraph import site |
| Channel adapters | `infrastructure/channels/` (WhatsApp, Telegram, API, base) |
| Error -> HTTP map | `drivers/api/responses.py` -- `domain_error_handler` |

## Bounded Contexts

| Context | Responsibility |
| ------- | -------------- |
| `auth` | Authentication, credential verification, JWT tokens, password hashing port |
| `tenants` | Multi-tenancy, tenant lifecycle (create, suspend, activate, rename) |
| `tenant_config` | Per-tenant configuration (LLM provider/model/key, embedding config, channel credentials) |
| `users` | User accounts, tenant memberships (`user_tenants`), owner registration |
| `contacts` | External people who interact with the front desk (channel senders resolved to entities) |
| `conversations` | Chat threads (`Conversation`) + individual messages (`Message`), tiered tool compression |
| `documents` | Uploaded files for the knowledge base, status machine (uploaded -> ingesting -> ready/failed) |
| `questions` | Escalated questions state machine (submitted -> resolved/closed), owner reply flow |
| `key_facts` | Remembered facts about contacts (preferences, context from past conversations) |
| `llm_usage` | Token usage tracking per-call with Decimal(18,8) cost, domain-side pricing table |
| `llm` | LLM domain port (`LLMClientPort`) + framework-agnostic value objects (LLMMessage, LLMCallResult) |
| `rag` | RAG domain ports (ChunkerPort, EmbeddingPort, RetrieverPort) + value objects (TextChunk, RetrievedChunk) |
| `telegram` | Telegram phone lookup table (telegram_user_id -> phone mapping for contact resolution) |
| `notifications` | Notification routing port + routing adapter (resolve best delivery channel for a recipient) |

**Naming:** Context folder names are plural where the domain concept is plural (`tenants`, `users`, `contacts`, `conversations`, `documents`, `questions`). Singular for domain capabilities (`auth`, `llm`, `rag`, `telegram`).

## Folder Structure

```text
src/
+-- domain/
|   +-- shared/
|   |   +-- entities.py           # BaseEntity: identity, equality, pending events, is_new
|   |   +-- events.py             # DomainEvent base (event_id, occurred_at via kw_only)
|   |   +-- exceptions.py         # DomainError -> EntityNotFoundError, AlreadyExistsError, etc.
|   |   +-- value_objects.py      # DateRange, SortOrder
|   |   +-- ports.py              # NotificationPort (cross-cutting)
|   |   +-- channel_result.py     # ChannelSendResult value object (sent/failed + metadata)
|   |   +-- media.py              # Pure text-parsing: extract_media() from LLM responses
|   |   +-- utils.py              # Pure domain utilities
|   +-- auth/
|   |   +-- ports.py              # PasswordHasher protocol
|   +-- tenants/
|   |   +-- entities.py           # Tenant aggregate (create, suspend, activate, rename)
|   |   +-- events.py             # TenantCreated, TenantSuspended, TenantActivated
|   |   +-- operations.py         # Domain helpers
|   |   +-- repositories.py       # TenantRepository port
|   |   +-- value_objects.py      # TenantStatus enum
|   +-- tenant_config/
|   |   +-- entities.py           # TenantConfig (LLM, embedding, channel credentials)
|   |   +-- repositories.py       # TenantConfigRepository port
|   |   +-- value_objects.py      # LLMProvider enum, etc.
|   +-- users/
|   |   +-- entities.py           # User, UserTenant
|   |   +-- events.py             # UserCreated, etc.
|   |   +-- repositories.py       # UserRepository, UserTenantRepository ports
|   |   +-- value_objects.py      # UserRole enum
|   +-- contacts/
|   |   +-- entities.py           # Contact aggregate (create, link_telegram)
|   |   +-- events.py             # ContactCreated
|   |   +-- repositories.py       # ContactRepository (get_or_create_by_phone, get_by_telegram_user_id)
|   +-- conversations/
|   |   +-- entities.py           # Conversation (start, touch), Message (create with tool fields)
|   |   +-- events.py             # ConversationStarted, MessageSaved
|   |   +-- repositories.py       # ConversationRepository, MessageRepository ports
|   |   +-- value_objects.py      # ConversationRole, ConversationChannel enums
|   +-- documents/
|   |   +-- entities.py           # Document (upload, mark_ingesting/ready/failed), Chunk (create)
|   |   +-- events.py             # DocumentUploaded, DocumentIngested, DocumentIngestionFailed
|   |   +-- repositories.py       # DocumentRepository, ChunkRepository ports
|   |   +-- value_objects.py      # DocumentStatus, DocumentMimeType enums
|   +-- questions/
|   |   +-- entities.py           # Question aggregate with state machine (submit, resolve, close)
|   |   +-- events.py             # QuestionSubmitted, QuestionResolved, QuestionClosed
|   |   +-- repositories.py       # QuestionRepository port
|   |   +-- value_objects.py      # QuestionStatus enum (submitted -> resolved | closed)
|   +-- key_facts/
|   |   +-- entities.py           # KeyFact entity
|   |   +-- repositories.py       # KeyFactRepository port (list_for_contact)
|   +-- llm/
|   |   +-- ports.py              # LLMClientPort protocol (chat_with_tools)
|   |   +-- value_objects.py      # LLMMessage, LLMMessageRole, LLMToolCall, LLMCallResult, TokenUsage
|   +-- llm_usage/
|   |   +-- entities.py           # TokenUsage entity (record factory with domain-side cost calc)
|   |   +-- events.py             # TokenUsageRecorded
|   |   +-- pricing.py            # ModelPricing table + calculate_cost() in Decimal(18,8)
|   |   +-- repositories.py       # TokenUsageRepository port
|   +-- rag/
|   |   +-- ports.py              # ChunkerPort, EmbeddingPort, RetrieverPort protocols
|   |   +-- value_objects.py      # TextChunk, RetrievedChunk
|   +-- notifications/
|   |   +-- entities.py           # Notification entity
|   |   +-- ports.py              # NotificationRoutingPort, ResolvedRoute, NotificationRoutingError
|   |   +-- repositories.py       # NotificationRepository port
|   +-- telegram/
|       +-- repositories.py       # TelegramPhoneRepository port (get_or_register)
|
+-- application/
|   +-- shared/
|   |   +-- unit_of_work.py       # UnitOfWork class -- single session, all repos
|   |   +-- event_collector.py    # Event collection utilities
|   |   +-- outbox_publisher.py   # Event outbox publishing
|   |   +-- pagination.py         # Shared pagination helpers
|   +-- auth/
|   |   +-- commands.py           # AuthenticateUser, RegisterOwner, ChangePassword, RefreshToken
|   |   +-- dtos.py               # AuthResultDTO, UserDTO
|   |   +-- use_cases/
|   |       +-- authenticate_user.py
|   |       +-- register_owner.py
|   |       +-- get_user_by_id.py
|   |       +-- change_password.py
|   |       +-- refresh_token.py
|   +-- conversations/
|   |   +-- commands.py           # SaveThreadMessage
|   |   +-- queries.py            # LoadThreadHistory
|   |   +-- dtos.py               # ThreadMessageDTO
|   |   +-- use_cases/
|   |       +-- save_thread_message.py   # Resolve-or-create conversation, save message
|   |       +-- load_thread_history.py   # Load messages for a thread
|   +-- documents/
|   |   +-- commands.py           # IngestDocument
|   |   +-- queries.py            # ListDocuments, RetrieveForQuery
|   |   +-- dtos.py               # DocumentDTO
|   |   +-- use_cases/
|   |       +-- ingest_document.py       # Parse, chunk, embed, persist
|   |       +-- list_documents.py
|   |       +-- retrieve_for_query.py
|   +-- questions/
|   |   +-- commands.py           # SubmitQuestion, ReplyToQuestion, CloseQuestion
|   |   +-- queries.py            # ListQuestions
|   |   +-- dtos.py               # QuestionDTO
|   |   +-- use_cases/
|   |       +-- submit_question.py
|   |       +-- reply_to_question.py
|   |       +-- close_question.py
|   |       +-- list_questions.py
|   |       +-- _mapping.py            # Shared entity-to-DTO mapping
|   +-- llm_usage/
|       +-- commands.py           # RecordTokenUsage
|       +-- queries.py            # GetUsageStats
|       +-- dtos.py               # UsageStatsDTO
|       +-- use_cases/
|           +-- record_token_usage.py
|           +-- get_usage_stats.py
|
+-- ai/                            # AI orchestration layer (cross-cutting)
|   +-- gateway.py                 # chat_with_agent(): the single public entry point
|   +-- types.py                   # ChatInput, ChatResult, ToolDef, ToolCallResult, AgentLoopResult
|   +-- concurrency.py            # Thread locking, message queuing
|   +-- agents/
|   |   +-- agent.py              # run_agent_loop(): LLM -> tool -> LLM cycle
|   +-- context/
|   |   +-- history.py            # load_history(): DB -> LLMMessage list + staleness hint
|   |   +-- memory.py             # load_key_facts_context(): inject known facts into prompt
|   |   +-- prompts.py            # build_asker_system_prompt(): system prompt builder
|   |   +-- checkpoint.py         # maybe_create_checkpoint(): token-budget conversation summaries
|   |   +-- i18n.py               # Internationalization context
|   +-- tools/
|   |   +-- types.py              # Tool type definitions
|   |   +-- search_documents.py   # RAG search tool
|   |   +-- escalate_question.py  # Question escalation tool
|   |   +-- save_key_fact.py      # Remember a fact about a contact
|   |   +-- remove_key_fact.py    # Forget a fact about a contact
|   +-- utils/
|       +-- sender.py             # resolve_sender(): channel user -> Contact entity
|       +-- tenant_llm.py         # Tenant LLM config helpers
|
+-- drivers/                       # Primary adapters (entry points)
|   +-- api/
|   |   +-- dependencies.py       # get_session, get_current_user, get_uow
|   |   +-- responses.py          # domain_error_handler: DomainError -> HTTP
|   |   +-- middleware/
|   |   |   +-- rate_limit.py     # Rate limiting
|   |   |   +-- request_id.py     # X-Request-ID propagation
|   |   +-- v1/
|   |   |   +-- router.py         # Top-level v1 router
|   |   |   +-- auth/             # Login, refresh
|   |   |   +-- tenants/          # Tenant CRUD
|   |   |   +-- users/            # User management
|   |   |   +-- conversations/    # Conversation history + messages
|   |   |   +-- documents/        # Document upload + list
|   |   |   +-- questions/        # Question management (list, reply, close)
|   |   |   +-- key_facts/        # Key facts CRUD
|   |   |   +-- llm_usage/        # Token usage stats
|   |   |   +-- settings/         # Tenant settings (LLM config, channel config)
|   |   |   +-- health/           # Health check endpoint
|   |   +-- webhooks/
|   |       +-- whatsapp.py       # Meta Cloud API webhook (verify + message handler)
|   |       +-- telegram.py       # Telegram Bot API webhook
|   |       +-- chat_api.py       # Direct API chat endpoint
|
+-- infrastructure/
|   +-- ai/
|   |   +-- graph.py              # LangGraph state graph (ONLY langgraph import site)
|   +-- auth/
|   |   +-- bcrypt_hasher.py      # BcryptPasswordHasher (implements PasswordHasher port)
|   |   +-- jwt_service.py        # JWT token creation + validation
|   +-- channels/
|   |   +-- base.py               # ChannelAdapter ABC, IncomingMessage, OutgoingMessage
|   |   +-- whatsapp.py           # WhatsAppAdapter (Meta Cloud API)
|   |   +-- telegram.py           # TelegramAdapter (Bot API)
|   |   +-- api.py                # Direct API channel adapter
|   |   +-- cache.py              # Channel adapter caching
|   |   +-- retry.py              # Retry decorators for channel sends
|   +-- llm/
|   |   +-- client.py             # LangChainLLMClient (implements LLMClientPort)
|   |   +-- circuit_breaker.py    # LLM call circuit breaker
|   |   +-- error_classifier.py   # Classify LLM errors (transient vs permanent)
|   |   +-- tenant_factory.py     # Per-tenant LLM client factory
|   |   +-- token_counter.py      # Token counting utilities
|   +-- rag/
|   |   +-- chunker.py            # RecursiveTokenChunker (tiktoken, ~512 tokens, 15% overlap)
|   |   +-- embedder.py           # OpenAIEmbedder (implements EmbeddingPort)
|   |   +-- parser.py             # Document parser (PDF, etc.)
|   |   +-- retriever.py          # HybridRetriever (vector HNSW + BM25 tsvector + RRF k=60)
|   +-- metrics/                   # Prometheus counters and histograms
|   +-- notifications/
|   |   +-- routing.py            # NotificationRoutingAdapter (resolve delivery channel)
|   |   +-- channel_sender.py     # Send via resolved channel
|   |   +-- context_loader.py     # Load context for notification formatting
|   +-- persistence/postgres/
|       +-- database.py           # Engine + session factory
|       +-- models/               # SQLAlchemy ORM models (one file per model)
|       |   +-- tenant.py, user.py, user_tenant.py, contact.py,
|       |     conversation.py, message.py, document.py, chunk.py,
|       |     question.py, key_fact.py, token_usage.py,
|       |     tenant_config.py, telegram_phone.py, outbox.py
|       +-- repositories/         # One file per entity
|           +-- tenant_repo.py, user_repo.py, user_tenant_repo.py,
|             contact_repo.py, conversation_repo.py, message_repo.py,
|             document_repo.py, chunk_repo.py, question_repo.py,
|             key_fact_repo.py, token_usage_repo.py,
|             tenant_config_repo.py, telegram_phone_repo.py, outbox_repo.py
|
+-- bootstrap/
|   +-- container.py              # DI container: singletons + use case factories
|   +-- events.py                 # Event bus wiring
|   +-- event_handlers.py         # Side-effect handlers for domain events
|
+-- config/
|   +-- settings.py               # Pydantic-settings (env-backed)
|   +-- logging.py                # Structured logging config
|
tests/
+-- unit/                          # domain, application, ai -- no IO; mock ports/repos
+-- integration/                   # infrastructure -- real PostgreSQL (frontdesk_test DB)
```

## Domain Module Files

| File | Purpose |
| ---- | ------- |
| `entities.py` | Rich domain entities with behavior methods, factory `create()` (or domain-verb like `submit()`, `upload()`, `start()`), invariant guards, and event emission |
| `value_objects.py` | Immutable types and enums (ConversationRole, QuestionStatus, DocumentMimeType, TenantStatus) |
| `repositories.py` | Persistence ports -- `save(entity)` for writes, `get_by_id()` / `get_by_thread_id()` for reads |
| `ports.py` | Gateway ports (LLMClientPort, EmbeddingPort, RetrieverPort, NotificationPort, PasswordHasher) |
| `operations.py` | (optional) Domain helpers -- pure functions that delegate to entity methods; no repo calls |
| `events.py` | Domain events (frozen dataclasses inheriting `DomainEvent`) |

**Domain cannot perform IO** (DB, network, filesystem, LLM calls). Keep domain pure and deterministic -- sync/async is allowed; IO is not.

## Domain Entities

Entities are **rich** -- they hold behavior, guard invariants, and emit domain events. No anemic data holders.

**Factory pattern:** Every entity has a factory classmethod that generates identity (`uuid4()`), sets defaults, and emits a `Created` event. The domain controls how entities are born, not the repository. Factory names match the domain verb:

| Entity | Factory | Why |
| ------ | ------- | --- |
| `Tenant` | `create()` | Generic creation |
| `Contact` | `create()` | Generic creation |
| `Conversation` | `start()` | A conversation starts |
| `Message` | `create()` | Generic creation |
| `Document` | `upload()` | Documents are uploaded |
| `Question` | `submit()` | Questions are submitted for escalation |
| `TokenUsage` | `record()` | Usage is recorded as a ledger entry |
| `Chunk` | `create()` | Generic creation |

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

**`kw_only=True`:** All entity dataclasses use `kw_only=True` so subclasses can declare required fields without dataclass ordering gymnastics around the parent's default-valued private fields.

**Event collection:** Entities collect events via `_emit()`. Use cases drain `pending_events` after a successful commit and dispatch via the event bus, then call `clear_events()`.

**Persistence detection:** `is_new` / `mark_persisted()` lets repos detect insert vs update in `save()`.

**Domain events:** All events inherit from `DomainEvent` base class which provides `event_id` (UUID) and `occurred_at` (datetime) via `kw_only=True` defaults.

## Domain Exceptions

All domain exceptions live in `domain/shared/exceptions.py` (shared, not per-context):

| Exception | HTTP Status | When |
| --------- | ----------- | ---- |
| `DomainError` | 400 | Base class for all domain errors |
| `EntityNotFoundError` | 404 | Entity does not exist |
| `AlreadyExistsError` | 400 | Uniqueness constraint violated |
| `AuthenticationError` | 401 | Bad credentials, expired tokens |
| `AuthorizationError` | 403 | Insufficient permissions |
| `InvalidOperationError` | 400 | Business rule violation (e.g. closing an already-closed question) |

**Mapping:** `drivers/api/responses.py` has a `domain_error_handler` registered on the FastAPI app that converts `DomainError` subclasses to HTTP responses. Each subclass declares its `http_status` so the mapping is open for extension without touching the handler. Use cases raise domain exceptions; they never raise `HTTPException`.

## CQRS

| Type | Location | Example |
| ---- | -------- | ------- |
| Command | `application/{context}/commands.py` | `SaveThreadMessage`, `IngestDocument`, `SubmitQuestion`, `ReplyToQuestion` |
| Query | `application/{context}/queries.py` | `LoadThreadHistory`, `ListDocuments`, `ListQuestions`, `GetUsageStats` |
| Use case | `application/{context}/use_cases/` | One file per use case; orchestrates domain, uow |

**Commands and queries are frozen dataclasses with typed fields** -- they carry input data for an operation and contain no business logic. Use cases receive them and perform the actual work.

**Command rules:**

- Use `@dataclass(frozen=True, kw_only=True)` -- commands are immutable parameter DTOs
- All fields must be **explicitly typed** -- never use `data: dict`
- Use **domain-level field names**, not API names
- API-to-domain name transformations happen at the **route layer**, not in use cases

```python
# Good -- typed fields with domain names
@dataclass(frozen=True, kw_only=True)
class ReplyToQuestion:
    tenant_id: UUID
    question_id: UUID
    replied_by_user_id: UUID
    reply: str

# Bad -- untyped dict
@dataclass(frozen=True)
class UpdateSomething:
    data: dict  # never do this
```

**DTOs:** Use cases accept commands/queries and return DTOs. Domain entities never leak to the API layer. DTOs live in `application/{context}/dtos.py`.

## Unit of Work

Frontdesk uses a single `UnitOfWork` class that wraps one `AsyncSession` and exposes all repositories as typed attributes. This is simpler than PropertyBot's per-context UoW approach because frontdesk has fewer cross-context writes.

```python
class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.tenants = PostgresTenantRepository(session)
        self.users = PostgresUserRepository(session)
        self.conversations = PostgresConversationRepository(session)
        self.messages = PostgresMessageRepository(session)
        self.documents = PostgresDocumentRepository(session)
        self.chunks = PostgresChunkRepository(session)
        self.questions = PostgresQuestionRepository(session)
        self.contacts = PostgresContactRepository(session)
        self.key_facts = PostgresKeyFactRepository(session)
        self.token_usages = PostgresTokenUsageRepository(session)
        self.tenant_configs = PostgresTenantConfigRepository(session)
        self.telegram_phones = PostgresTelegramPhoneRepository(session)
        # ...

    async def flush(self) -> None: ...   # push without commit (FK chains)
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

**Session lifecycle:** Each route handler opens one session via `get_session()`, creates a UoW, commits on success, rolls back on error. Use cases interact ONLY with the UoW -- never the session directly.

**Flush pattern:** Use `uow.flush()` between an insert and an FK-referencing insert in the same transaction (e.g. creating a Contact then saving a Message that references the contact's ID).

## Flow

The full lifecycle from inbound message to AI response, using the gateway as the canonical example:

```text
Webhook/API -> chat_with_agent(ChatInput, uow):
    0. Load tenant config (per-tenant LLM + embedding creds from DB)
       Validate: LLM API key must be configured
    0b. Resolve sender -> Contact via resolve_sender()
        - WhatsApp: get_or_create_by_phone
        - Telegram: lookup telegram_phones table -> get_or_create_by_phone
        - API/Web: get_or_create_by_phone with identifier
    1. Save inbound USER message via SaveThreadMessageUseCase
       (resolves-or-creates Conversation, saves Message, bumps timestamps)
    2. Load conversation history from DB (source of truth)
    3. Build system prompt + inject key_facts context if contact known
    4. Build LLM client + embedder + retriever from tenant config
    5. Build and run LangGraph agent:
       call_llm -> (tool_call?) -> execute_tools -> call_llm -> ... -> END
       Max 5 iterations safety cap
    6. Save all tool exchanges as hidden ASSISTANT + TOOL messages
       Save final ASSISTANT reply as visible message
    7. Record token usage (input, output, cache_read) with domain-side cost calc
    8. Maybe create checkpoint if token budget exceeded (3000 tokens since last)
    9. Return ChatResult (response text, thread_id, escalated flag, request_id)

Webhook handler commits UoW, then sends reply via channel adapter
```

**Repository `save()` pattern:** Repos expose `save(entity)` instead of separate `create(fields)` / `update(fields)`. The repo checks `entity.is_new` to decide INSERT vs UPDATE. After insert, it calls `entity.mark_persisted()`.

## Repository Pattern

```python
# Domain port (in domain/{context}/repositories.py):
class ContactRepository(Protocol):
    async def get_or_create_by_phone(self, tenant_id: UUID, phone: str, name: str | None = None) -> Contact: ...
    async def get_by_telegram_user_id(self, tenant_id: UUID, telegram_user_id: str) -> Contact | None: ...
    async def save(self, contact: Contact) -> None: ...
    async def get_by_id(self, contact_id: UUID) -> Contact | None: ...

# Infrastructure implementation (in infrastructure/persistence/postgres/repositories/contact_repo.py):
class PostgresContactRepository:
    def __init__(self, session: AsyncSession): ...
    async def save(self, contact: Contact) -> None:
        if contact.is_new:
            # INSERT
            contact.mark_persisted()
        else:
            # UPDATE
```

**`get_or_create_by_phone`:** The Contact repo implements an upsert pattern using `INSERT ON CONFLICT` for phone uniqueness scoped to `(tenant_id, phone)`. This is critical for webhook idempotency -- multiple messages from the same sender must not create duplicate contacts.

## Contact Model

Contacts are external people who interact with a tenant's front desk. They are simpler than PropertyBot's Client entity -- no lead management, no blocking, no global-vs-tenant split. Just identity + tenant scope.

**How channel contacts become real entities:**

1. **WhatsApp:** `resolve_sender()` calls `get_or_create_by_phone(tenant_id, phone)` -- phone is the natural key from the Meta webhook payload.

2. **Telegram:** Two-step resolution via the `telegram_phones` table:
   - `uow.telegram_phones.get_or_register(telegram_user_id)` -- returns phone if user has shared it, otherwise registers the unknown user_id
   - If phone found: `get_or_create_by_phone(tenant_id, phone)`, then `contact.link_telegram(telegram_user_id)` to associate the Telegram identity
   - If no phone: return `None` -- contact cannot be created until the user shares their phone number (the unique key)

3. **API / Web / Owner Dashboard:** Treats the sender identifier as a phone-like key, same `get_or_create_by_phone` flow.

**Why this matters:** The contact resolution happens before any message is saved, so every message in the DB has a real `participant_id` (or `None` for unresolved Telegram users). This drives key facts loading, question attribution, and notification routing.

## Channel Infrastructure

```text
ChannelAdapter (ABC)
|-- parse_incoming(raw_payload) -> IncomingMessage
|-- send_text(recipient, text) -> dict | None
|-- send_voice(recipient, audio, mime_type) -> None
|-- send_image(recipient, url, caption) -> None
|-- send_video(recipient, url, caption) -> None
|-- send_document(recipient, url, caption) -> None
|-- send_media_group(recipient, urls, caption) -> dict | None
|-- send_structured(recipient, clean_text, media) -> ChannelSendResult
|-- send_response(recipient, text) -> ChannelSendResult     # extract_media() then send_structured()
|
+-- WhatsAppAdapter (Meta Cloud API v23.0)
|   - Credentials from TenantConfig (phone_number_id, access_token, verify_token)
|   - send_text: POST to graph.facebook.com/{phone_number_id}/messages
|   - send_image/video/document: native rich media via Meta API
|   - send_media_group: no album API, sends sequentially with delay
|   - verify_signature: HMAC-SHA256 with replay protection
|   - _get_media_url: resolve media_id to download URL for voice/image
|
+-- TelegramAdapter (Bot API)
|   - Credentials from TenantConfig (telegram_bot_token)
|   - send_text: sendMessage with HTML parse_mode, fallback to plain text
|   - send_image: sendPhoto API
|   - send_media_group: sendMediaGroup (native album), fallback to plain caption
|   - send_video: sendVideo API
|   - send_document: sendDocument API
|   - send_contact_request: keyboard button for phone number sharing
|   - Text auto-chunked at 4096 chars (Telegram limit)
|
+-- APIAdapter (Direct)
    - For programmatic chat via REST API
```

**Retry infrastructure:** All channel sends use `@channel_send_retry()` decorator for transient failure handling. WhatsApp has configurable delay between album images (`WHATSAPP_IMAGE_SEND_DELAY_SECONDS`) and max images per album (`WHATSAPP_MAX_IMAGES_PER_ALBUM`).

**Media extraction:** The `send_response()` method on the base adapter calls `extract_media()` (from `domain/shared/media.py`) to parse `<<<IMAGES>>>`, `<<<VIDEOS>>>`, `<<<DOCUMENTS>>>` blocks and markdown image syntax from LLM responses, then sends native rich media per-channel.

## Notification Routing

Notifications are channel-agnostic. The routing adapter resolves the best delivery channel for a recipient:

```text
NotificationRoutingPort.resolve_route(tenant_id, recipient_id, recipient_type)
    |
    +-- Step 1: Find most recent conversation for this recipient+tenant -> send there
    +-- Step 2: Tenant has WhatsApp configured + recipient has phone -> WhatsApp thread
    +-- Step 3: Recipient has telegram_user_id -> Telegram thread
    +-- Step 4: All failed -> raise NotificationRoutingError
```

Returns a `ResolvedRoute(channel, thread_id, conversation_id, tenant_id, recipient_id)`. The `channel_sender.py` then sends via the resolved channel adapter.

## RAG Pipeline

```text
Document upload -> Ingest:
    1. Parse: infrastructure/rag/parser.py extracts text from PDF, DOCX, TXT, etc.
    2. Chunk: RecursiveTokenChunker splits on natural boundaries
       (paragraph -> line -> sentence -> word -> char)
       Target: ~512 tokens per chunk, ~15% overlap
       Sizing: tiktoken (o200k_base encoding)
    3. Embed: OpenAIEmbedder calls OpenAI embeddings endpoint
       Per-tenant API key + model + dimensions from TenantConfig
    4. Persist: Each Chunk row stores content + embedding vector + extra_metadata
       HNSW index (cosine ops) + GIN index (tsvector) on chunks table

Query-time retrieval:
    1. Vector search: HNSW cosine distance, top-50 candidates
    2. BM25 search: websearch_to_tsquery + ts_rank over tsvector, top-50 candidates
    3. Reciprocal Rank Fusion (RRF, k=60): combine ranks from both sources
       score(doc) = sum(1 / (k + rank)) across lists
    4. Return top-k (default 8) RetrievedChunk objects

    Every query filters by tenant_id -- never trust callers to scope.
```

**Tenant isolation:** Both vector and BM25 queries include `WHERE tenant_id = :tid`. This is enforced at the infrastructure layer, not left to callers.

**Future:** The `RetrievedChunk` shape carries enough metadata to feed a cross-encoder reranker (Step 5) when added.

## AI Orchestration

The AI layer has three key components:

### Gateway (`ai/gateway.py`)

Single public entry point: `chat_with_agent(ChatInput, uow) -> ChatResult`. Every channel (WhatsApp webhook, Telegram webhook, Chat API) calls this. The gateway:

1. Loads tenant's LLM config from DB (per-tenant, not `.env`)
2. Resolves sender to a Contact entity
3. Saves the inbound message
4. Loads history from DB (source of truth)
5. Builds system prompt + tool definitions + key facts context
6. Runs the LangGraph agent (infrastructure/ai/graph.py)
7. Saves tool exchanges + assistant reply
8. Records token usage with domain-side cost calculation
9. Creates a conversation checkpoint if token budget exceeded
10. Returns response text for the channel to send back

### Agent Loop (`ai/agents/agent.py` + `infrastructure/ai/graph.py`)

Two implementations exist -- the graph-based one (`infrastructure/ai/graph.py`) is the active path:

```text
call_llm -> should_continue?
    |-- has tool_calls + iteration < 5 -> execute_tools -> call_llm (loop)
    |-- no tool_calls or iteration >= 5 -> END
```

**LangGraph isolation:** `infrastructure/ai/graph.py` is the ONLY file importing `langgraph`. It translates between domain value objects (`LLMMessage`) and LangChain message types (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`) at the boundary. The rest of `ai/` never sees LangGraph or LangChain types.

**Per-turn only:** The graph runs fresh per turn with no checkpointer. The DB messages table is the cross-turn source of truth. This trades a small amount of glue code for transparent queries, a readable admin UI, and version-independent persistence.

### Available Tools

| Tool | Purpose | Implementation |
| ---- | ------- | -------------- |
| `search_documents` | RAG retrieval from the tenant's knowledge base | Calls `HybridRetriever.hybrid_retrieve()` |
| `escalate_question` | Escalate a question the AI cannot answer to the owner | Creates a `Question` entity via `SubmitQuestionUseCase` |
| `save_key_fact` | Remember a fact about the current contact | Persists to `key_facts` table |
| `remove_key_fact` | Forget a previously saved fact | Removes from `key_facts` table |

Tools are defined as framework-agnostic `ToolDef` objects (name, description, JSON Schema parameters). The graph's `_dispatch_tool()` routes by tool name to the concrete runner function.

### System Prompt

The system prompt (`ai/context/prompts.py`) instructs the agent to:

1. ALWAYS search the knowledge base first before answering factual questions
2. Answer based ONLY on search results -- do not guess
3. Escalate if no results found or not confident
4. Escalate immediately if user asks to speak with a person
5. Keep answers concise (1-3 sentences)
6. Match the language the asker uses

### Context Loading

- **History** (`ai/context/history.py`): Loads messages from DB via `LoadThreadHistoryUseCase`. Maps `ConversationRole` to `LLMMessageRole`. Injects a staleness hint if the conversation went quiet for 30+ minutes.
- **Memory** (`ai/context/memory.py`): Loads key facts for the current contact and appends them to the system prompt (e.g. "Known facts about this asker: - name: John - preference: quick responses").
- **Checkpoint** (`ai/context/checkpoint.py`): After each agent response, checks if total tokens since last checkpoint exceed 3000. If so, generates a structured JSON summary compressing the conversation into current active state.

## Tiered Tool Compression

Frontdesk preserves tool exchanges in their native format so the LLM sees them as `tool_use` / `tool_result` blocks:

```text
Message fields for tool exchanges:
- tool_call_id    : str | None     # tool name (set on ASSISTANT messages with tool_calls)
- tool_args       : dict | None    # tool arguments (JSONB)
- tool_result     : dict | None    # tool result (set on TOOL messages)
- is_compressed   : bool           # set when older exchanges get rolled up
- compressed_summary : str | None  # human-readable summary after compression
```

**Recent exchanges** stay verbatim (`tool_use` / `tool_result` blocks the LLM was trained on). **Older exchanges** get rolled up via the checkpoint system to a structured summary, while the original `tool_args` / `tool_result` are retained in JSONB for UUID-driven recovery.

The history loader (`ai/context/history.py`) uses `compressed_summary` if `is_compressed` is true, otherwise uses the original `content`. Hidden messages are filtered out (except checkpoints which are included).

## Token + Cost Ledger

Every LLM call writes a `TokenUsage` row via the domain entity factory:

```python
TokenUsage.record(
    tenant_id=..., provider="anthropic", model="claude-sonnet-4-5",
    input_tokens=1200, output_tokens=300, cache_read_tokens=800,
    thread_id=..., request_id=..., source="asker", channel="whatsapp",
)
```

The factory calls `calculate_cost()` from `domain/llm_usage/pricing.py` which looks up per-million USD rates and computes cost in `Decimal(18,8)`. Pricing lives domain-side so the cost math stays testable without infrastructure. Aggregation happens in SQL, not in Python.

**Supported models:** Claude Opus 4.5, Claude Sonnet 4.5, Claude Haiku 4.5, GPT-4o, GPT-4o-mini, Gemini 2.0 Flash. Unknown models cost $0 (logged elsewhere).

## Forbidden Imports

| Layer | Cannot import from |
| ----- | ------------------ |
| `domain/` | `application/`, `infrastructure/`, `drivers/`, `ai/`, `config/` |
| `application/` | `infrastructure/`, `drivers/`, `ai/` |
| `infrastructure/` | `drivers/`, `application/`, `ai/` |
| `ai/` | `infrastructure/` (except `infrastructure/metrics` and `infrastructure/ai/graph`), `drivers/` |

**Application layer must never:**
- Import `HTTPException` or any FastAPI exception
- Import concrete infrastructure classes (e.g. `PostgresContactRepository`)
- Raise `ValueError` for business errors (use domain exceptions)

**AI layer imports (explicit):**
- `ai/` -> `application/` (use cases, commands, queries)
- `ai/` -> `domain/` (value objects, ports, exceptions)
- `ai/` -> `infrastructure/metrics` (Prometheus counters -- pragmatic exception)
- `infrastructure/ai/graph.py` imports `langgraph` and `langchain_core.messages` -- this is the ONLY such import site
- Agent tools must call use cases, never repos or ORM models directly. Context loading goes through application use cases.

**Note on gateway.py:** The gateway currently imports `LangChainLLMClient`, `OpenAIEmbedder`, and `HybridRetriever` directly from infrastructure. This is a known shortcut for v1 -- these should be injected via the DI container in a future refactor. The `infrastructure/ai/graph.py` import is done via lazy `import` inside the function body.

**Verify with:**

```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" src/application/
# Should be empty.

grep -rn "^from langchain\|^from langgraph" src/domain/ src/application/
# Should be empty.
```

## Concurrency & Idempotency

### Webhook Deduplication

WhatsApp and Telegram webhooks can deliver the same event more than once. The system handles this through:

- **Contact resolution:** `get_or_create_by_phone` uses `INSERT ON CONFLICT` -- duplicate messages from the same sender are safe.
- **Conversation resolution:** `get_by_thread_id` finds existing threads by the deterministic `thread_id` (e.g. `whatsapp:{phone}:{tenant_id}`). Duplicate webhooks get the same conversation.
- **Message persistence:** Each message gets a unique UUID. Duplicate webhook deliveries create separate message rows (idempotency at the conversation level, not the message level). This is acceptable because the AI response is the side effect, not the message storage.

### DB Constraints as Safety Net

- `(tenant_id, phone)` unique on contacts -- prevents duplicate contacts
- `thread_id` unique on conversations -- prevents duplicate threads
- `(tenant_id, slug)` unique on tenants -- prevents duplicate tenants

Application validation provides good UX; DB constraints enforce truth. Never rely solely on app-level checks for uniqueness.

### Webhook Signature Verification

- **WhatsApp:** HMAC-SHA256 verification via `X-Hub-Signature-256` header with optional replay protection (timestamp check, configurable max age).
- **Telegram:** Webhook validation handled at the bot registration level.

## Testing Strategy

| Layer | Scope | Approach |
| ----- | ----- | -------- |
| Unit | `domain/`, `application/`, `ai/` | No IO; mock ports and repositories. Tests cover entity factories, state machines, domain rules, agent loop behavior, checkpoint logic. |
| Integration | `infrastructure/`, full flows | Real PostgreSQL (`frontdesk_test` database). Tests cover repo CRUD, use case flows end-to-end, API routes, webhook handling. |

Domain and application tests must not import infrastructure. Use cases accept commands/queries and return DTOs -- test via the use case interface.

**Current test coverage includes:**
- Entity behavior (base entity, question state machine, document status transitions)
- Agent loop (tool dispatch, max iterations, error handling)
- Checkpoint creation and JSON parsing
- Auth flows (register, authenticate, refresh, change password)
- Conversation persistence and history loading
- Document ingestion pipeline
- Question lifecycle (submit, reply, close)
- Key facts CRUD
- LLM usage recording
- Settings management
- Channel webhook handling

## Adding a Feature

Step-by-step guide for adding a new feature (e.g. a new entity, a new tool, a new API endpoint):

### 1. Domain (pure business logic)

```text
src/domain/{context}/
+-- entities.py      Add entity with create() factory, behavior methods, invariant guards, _emit() events
+-- events.py        Add domain events (frozen dataclasses inheriting DomainEvent)
+-- repositories.py  Add repository port with save(), get_by_id(), etc.
+-- value_objects.py  Add enums, status types, etc.
+-- ports.py          Add gateway ports if the entity needs external services
```

### 2. Application (orchestration)

```text
src/application/{context}/
+-- commands.py       Add command (frozen kw_only dataclass, typed fields, domain names)
+-- queries.py        Add query (frozen kw_only dataclass)
+-- dtos.py           Add DTO for use case output
+-- use_cases/
    +-- {verb}_{noun}.py   One file per use case; accept command/query, call entity, save, return DTO
```

Add the new repo to `application/shared/unit_of_work.py` if needed.

### 3. Infrastructure (adapters)

```text
src/infrastructure/persistence/postgres/
+-- models/{entity}.py            SQLAlchemy ORM model (one file per model)
+-- repositories/{entity}_repo.py  Concrete repo implementing the domain port
```

Wire the new repo into the UoW constructor in `application/shared/unit_of_work.py`.

Create an Alembic migration: `uv run alembic revision --autogenerate -m "add {entity} table"`.

### 4. API / AI (entry points)

For API endpoints:

```text
src/drivers/api/v1/{context}/
+-- routes.py        Add route that creates command/query, calls use case, returns response
+-- schemas.py       Add Pydantic request/response schemas (API-level names, transformed to domain names)
```

Register the router in `drivers/api/v1/router.py`.

For AI tools:

```text
src/ai/tools/
+-- {tool_name}.py    Add ToolDef (name, description, parameters_schema) + runner function
```

Register the tool in `ai/gateway.py` (`_TOOLS` list) and add dispatch case in `infrastructure/ai/graph.py` (`_dispatch_tool()`).

### 5. Tests

- Unit test the entity (factory, behavior, invariants, events) in `tests/unit/`
- Unit test the use case (mock repos, verify orchestration) in `tests/unit/`
- Integration test the repo + route in `tests/integration/`

### 6. Verify

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --tb=short -q
```
