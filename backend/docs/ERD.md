# Frontdesk Database ERD

Entity Relationship Diagram for `src/infrastructure/persistence/postgres/models`.

---

## Diagram

```
 ┌─────────────────────┐
 │      tenants         │
 ├─────────────────────┤
 │ id            PK     │
 │ name                 │
 │ slug          UQ IDX │
 │ status               │
 │ created_at           │
 │ updated_at           │
 └──────────┬──────────┘
            │
            │ 1
            │
    ┌───────┴────────────────────────────────────────────────────────────────┐
    │       │            │            │           │          │               │
    │ N     │ N          │ N          │ N         │ N        │ N             │ N
    ▼       ▼            ▼            ▼           ▼          ▼               ▼
┌────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌────────────┐ ┌──────────────┐
│contacts│ │conversa- │ │documents │ │questions│ │key_    │ │token_      │ │tenant_       │
│        │ │tions     │ │          │ │         │ │facts   │ │usages      │ │configs       │
├────────┤ ├──────────┤ ├──────────┤ ├─────────┤ ├────────┤ ├────────────┤ ├──────────────┤
│id   PK │ │id     PK │ │id     PK │ │id    PK │ │id   PK │ │id       PK │ │id         PK │
│tenant_ │ │tenant_   │ │tenant_   │ │tenant_ │ │tenant_ │ │tenant_     │ │tenant_id     │
│  id FK │ │  id   FK │ │  id  FK  │ │  id FK │ │  id FK │ │  id     FK │ │  UQ FK       │
│phone   │ │thread_id │ │uploaded_ │ │conver- │ │contact_│ │thread_id   │ │llm_provider  │
│  UQ*   │ │  UQ IDX  │ │  by_user_│ │sation_ │ │  id FK │ │request_id  │ │llm_model     │
│name    │ │channel   │ │  id FK   │ │  id FK │ │key     │ │source      │ │llm_api_key   │
│email   │ │partici-  │ │filename  │ │channel │ │value   │ │channel     │ │llm_max_tokens│
│telegram│ │  pant_   │ │mime_type │ │contact_│ │created_│ │provider    │ │llm_temp      │
│_user_id│ │  id FK   │ │size_bytes│ │  id FK │ │  at    │ │model       │ │embedding_*   │
│created_│ │created_at│ │status    │ │question│ │updated_│ │input_      │ │whatsapp_*    │
│  at    │ │updated_at│ │chunk_    │ │  _text │ │  at    │ │  tokens    │ │telegram_*    │
│updated_│ │last_msg_ │ │  count   │ │ai_answer│ │        │ │output_     │ │bot_name      │
│  at    │ │  at      │ │error     │ │  _attempt│ │       │ │  tokens    │ │bot_welcome   │
└───┬────┘ │          │ │created_at│ │status  │ └────────┘ │cache_read_ │ │bot_language   │
    │      │          │ │updated_at│ │owner_  │            │  tokens    │ │created_at    │
    │      └────┬─────┘ └────┬─────┘ │  reply │            │input_cost  │ │updated_at    │
    │           │            │       │replied_│            │cache_read_ │ └──────────────┘
    │           │            │       │  by_   │            │  cost      │
    │           │ 1          │ 1     │  user_ │            │output_cost │
    │           │            │       │  id FK │            │created_at  │
    │           ▼ N          ▼ N     │replied_│            └────────────┘
    │      ┌──────────┐ ┌──────────┐ │  at    │
    │      │messages   │ │chunks    │ │created_│
    │      ├──────────┤ ├──────────┤ │  at    │
    │      │id      PK│ │id     PK │ │updated_│
    │      │conversa- │ │document_ │ │  at    │
    │      │  tion_   │ │  id   FK │ └────────┘
    │      │  id   FK │ │tenant_   │
    │      │tenant_   │ │  id   FK │
    │      │  id   FK │ │chunk_    │
    │      │role      │ │  index   │
    │      │content   │ │content   │
    │      │hidden    │ │embedding │
    │      │tool_call_│ │  vector  │
    │      │  id      │ │  (1536)  │
    │      │tool_args │ │content_  │
    │      │tool_     │ │  tsvector│
    │      │  result  │ │  (GIN)  │
    │      │is_com-   │ │extra_   │
    │      │  pressed │ │  metadata│
    │      │compressed│ │created_at│
    │      │  _summary│ └──────────┘
    │      │is_check- │
    │      │  point   │
    │      │token_    │
    │      │  count   │
    │      │request_id│
    │      │created_at│
    │      └──────────┘
    │
    │
    ▼
┌───────────────────────┐         ┌──────────────────────┐
│    user_tenants        │         │       users           │
├───────────────────────┤         ├──────────────────────┤
│ id               PK    │         │ id             PK     │
│ user_id    FK ────────┼────────►│ email          UQ IDX │
│ tenant_id  FK ────────┼──┐      │ hashed_password       │
│ role                   │  │      │ full_name             │
│ joined_at              │  │      │ is_active             │
│ UQ(user_id, tenant_id) │  │      │ created_at            │
└───────────────────────┘  │      │ updated_at            │
                           │      └──────────────────────┘
                           │
                           └─► tenants (FK)


┌──────────────────────────┐      ┌──────────────────────────┐
│     telegram_phones       │      │      outbox_events        │
├──────────────────────────┤      ├──────────────────────────┤
│ telegram_user_id   PK     │      │ id                PK      │
│ phone                     │      │ event_type         IDX    │
│ created_at                │      │ event_data         JSONB  │
│ updated_at                │      │ tenant_id          IDX    │
└──────────────────────────┘      │ delivered          IDX    │
                                  │ created_at         IDX    │
                                  │ delivered_at              │
                                  │ error                     │
                                  └──────────────────────────┘
```

---

## Tables Overview

### Core

| Table | Purpose |
| ----- | ------- |
| **tenants** | Business accounts. Multi-tenant root. Fields: name, slug (unique), status (active/suspended). |
| **tenant_configs** | Per-tenant configuration: LLM provider/model/key, embedding config, WhatsApp and Telegram credentials, bot personality (name, welcome message, language). One row per tenant (unique constraint). |
| **users** | Owner accounts. Fields: email (unique), hashed_password, full_name, is_active. |
| **user_tenants** | User membership in a tenant. Many-to-many with role (owner). Unique constraint on (user_id, tenant_id). |

### Contacts & Conversations

| Table | Purpose |
| ----- | ------- |
| **contacts** | External people who interact with a tenant's front desk. Identified by phone (unique per tenant). Optional: name, email, telegram_user_id. |
| **telegram_phones** | Maps Telegram user IDs to phone numbers for contact resolution. Standalone table (no tenant FK) — Telegram user identity is global. |
| **conversations** | Chat threads. One per participant + tenant + channel. Identified by unique `thread_id` (e.g. `whatsapp:{phone}:{tenant_id}`). FK to contacts via `participant_id`. |
| **messages** | Append-only chat log. Fields: role (user/assistant/tool), content, hidden flag. Tool exchange fields: `tool_call_id`, `tool_args` (JSONB), `tool_result` (JSONB). Compression fields: `is_compressed`, `compressed_summary`. Checkpoint: `is_checkpoint`, `token_count`. |

### Knowledge Base

| Table | Purpose |
| ----- | ------- |
| **documents** | Uploaded files for the RAG knowledge base. Status machine: uploaded -> ingesting -> ready / failed. Tracks filename, mime_type, size_bytes, chunk_count, error. FK to users via `uploaded_by_user_id`. |
| **chunks** | Text slices from documents with embeddings. Fields: content, `embedding` (vector(1536) with HNSW index), `content_tsvector` (generated column with GIN index), chunk_index, extra_metadata (JSONB). FK to documents and tenants. |

### Escalations

| Table | Purpose |
| ----- | ------- |
| **questions** | Escalated questions with full lifecycle. Fields: question_text, ai_answer_attempt, status (submitted/resolved/closed), owner_reply, replied_by_user_id, replied_at. FKs to tenants, conversations, contacts, users. |

### AI Memory

| Table | Purpose |
| ----- | ------- |
| **key_facts** | Key-value facts about a contact within a tenant (preferences, name, context from past conversations). Unique constraint on (tenant_id, contact_id, key). Used as AI memory context. |

### Usage & Infrastructure

| Table | Purpose |
| ----- | ------- |
| **token_usages** | LLM token usage tracking per call. Fields: provider, model, source, channel, input/output/cache_read tokens, input/cache_read/output cost as Decimal(18,8). Indexed by tenant_id, thread_id, request_id, created_at. |
| **outbox_events** | Transactional outbox for reliable domain event publishing. Fields: event_type, event_data (JSONB), tenant_id, delivered flag, delivered_at, error. |

---

## Key Constraints

| Constraint | Table | Purpose |
| ---------- | ----- | ------- |
| `uq_contacts_tenant_phone` | contacts | `(tenant_id, phone)` — prevents duplicate contacts per tenant |
| `thread_id` UNIQUE | conversations | Prevents duplicate threads |
| `uq_user_tenant` | user_tenants | `(user_id, tenant_id)` — one membership per user per tenant |
| `uq_tenant_config_tenant` | tenant_configs | One config row per tenant |
| `uq_key_fact_per_contact` | key_facts | `(tenant_id, contact_id, key)` — one value per fact per contact |
| `slug` UNIQUE | tenants | Globally unique tenant slugs |
| `email` UNIQUE | users | Globally unique user emails |
| `ix_chunks_embedding_hnsw` | chunks | HNSW index on embedding (cosine ops) for vector search |
| `ix_chunks_content_tsvector_gin` | chunks | GIN index on tsvector for BM25 keyword search |

---

## Foreign Key Cascade Rules

| Parent | Child | On Delete |
| ------ | ----- | --------- |
| tenants | contacts, conversations, messages, documents, chunks, questions, key_facts, token_usages, tenant_configs, user_tenants | CASCADE |
| users | user_tenants | CASCADE |
| users | documents (uploaded_by_user_id), questions (replied_by_user_id) | SET NULL |
| contacts | conversations (participant_id), questions (contact_id) | SET NULL |
| contacts | key_facts | CASCADE |
| conversations | messages, questions (conversation_id) | CASCADE / SET NULL |
| documents | chunks | CASCADE |
