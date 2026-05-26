# Channel Integration

Frontdesk supports three inbound channels: WhatsApp (Meta Cloud API), Telegram (Bot API), and a direct Chat API. All channels funnel into the same gateway (`chat_with_agent`), with channel adapters handling protocol-specific parsing and delivery.

> **Source of truth:** The code. If this document disagrees with the code, the code wins -- update the doc in the same change.

---

## Architecture Overview

```text
                                    INBOUND
                                    ───────
  WhatsApp Cloud API  ─→  POST /webhooks/{tenant_id}/whatsapp
  Telegram Bot API    ─→  POST /webhooks/{tenant_id}/telegram
  Authenticated user  ─→  POST /api/v1/chat

        │                     │                      │
        ▼                     ▼                      ▼
  parse payload          parse update           validate auth
  verify signature       verify secret          resolve tenant
        │                     │                      │
        └─────────────────────┼──────────────────────┘
                              ▼
                    chat_with_agent(ChatInput, uow)
                              │
                              ▼
                         ChatResult
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
  WhatsAppAdapter        TelegramAdapter          JSON response
  .send_text()           .send_text()
  .send_response()       .send_response()

                                    OUTBOUND (notifications)
                                    ────────────────────────
        │
        ├── Step 1: existing conversation → send there
        ├── Step 2: WhatsApp configured + phone → WhatsApp thread
        ├── Step 3: telegram_user_id → Telegram thread
```

---

## ChannelAdapter Abstract Base

**File:** `infrastructure/channels/base.py`

All channel adapters inherit from `ChannelAdapter` ABC. The base class defines the contract and provides default implementations for structured media sending.

### Abstract Methods (must override)

| Method | Signature | Purpose |
| ------ | --------- | ------- |
| `parse_incoming` | `(raw_payload: dict) -> IncomingMessage` | Parse channel-specific webhook payload into a unified message |
| `send_text` | `(recipient: str, text: str) -> dict | None` | Send a plain text message |
| `send_voice` | `(recipient: str, audio: bytes, mime_type: str) -> None` | Send a voice message |

### Concrete Methods (with defaults, overridable)

| Method | Purpose |
| ------ | ------- |
| `send_image` | Send an image; default falls back to text with URL |
| `send_video` | Send a video; default falls back to text with URL |
| `send_document` | Send a document; default falls back to text with URL |
| `send_media_group` | Send multiple images as album; default sends sequentially |
| `send_structured` | Send pre-extracted text + media; returns `ChannelSendResult` |
| `send_response` | Extract media from LLM response, then delegate to `send_structured` |

### Data Types

```python
@dataclass
class IncomingMessage:
    channel: str                        # "whatsapp", "telegram", "api"
    sender_phone: str                   # phone or chat_id
    message_type: MessageType           # text, voice, image, document, location
    text: str
    media_url: str
    raw_payload: dict
    thread_id: str
    metadata: dict                      # channel-specific extras

class MessageType(StrEnum):
    TEXT, VOICE, IMAGE, DOCUMENT, LOCATION
```

### Media Extraction Pipeline

The `send_response()` method calls `extract_media()` from `domain/shared/media.py` to parse media blocks from LLM responses:

- `<<<IMAGES>>>...<<<END_IMAGES>>>` blocks
- `<<<VIDEOS>>>...<<<END_VIDEOS>>>` blocks
- `<<<DOCUMENTS>>>...<<<END_DOCUMENTS>>>` blocks
- Markdown image syntax `![alt](url)`

After extraction, `send_structured()` sends the clean text via `send_text()` and each media item via the channel's native media API.

---

## WhatsApp Adapter

**File:** `infrastructure/channels/whatsapp.py` -- `WhatsAppAdapter`

Uses the Meta Cloud API v23.0. Credentials come from `TenantConfig` (per-tenant, stored in DB).

### Configuration

| Field | Source |
| ----- | ------ |
| `phone_number_id` | `TenantConfig.whatsapp_phone_number_id` |
| `access_token` | `TenantConfig.whatsapp_access_token` |
| `verify_token` | `TenantConfig.whatsapp_verify_token` |
| `app_secret` | `TenantConfig.whatsapp_app_secret` |

### Incoming Message Parsing

Extracts the first message from the Meta webhook payload structure:

```text
entry[0].changes[0].value.messages[0]
```

Supports message types: text, audio (voice), image (with caption), interactive (button/list replies), location.

For voice and image messages, resolves `media_id` to a download URL via `GET graph.facebook.com/{media_id}`.

### Outbound Sends

All sends POST to `graph.facebook.com/v23.0/{phone_number_id}/messages`.

| Method | Meta API payload type | Notes |
| ------ | -------------------- | ----- |
| `send_text` | `type: "text"` | Strips leading `+` from phone |
| `send_image` | `type: "image"`, link + caption | `@channel_send_retry()` decorated |
| `send_video` | `type: "video"`, link + caption | `@channel_send_retry()` decorated |
| `send_document` | `type: "document"`, link + caption + filename | Extracts filename from URL |
| `send_voice` | `type: "audio"`, uploaded media ID | Uploads audio first, then sends |
| `send_media_group` | No native album API | Sends sequentially with configurable delay |

**Album sending:** WhatsApp has no native album API. Images are sent sequentially with `WHATSAPP_IMAGE_SEND_DELAY_SECONDS` delay between them, capped at `WHATSAPP_MAX_IMAGES_PER_ALBUM`.

### Signature Verification

**File:** `WhatsAppAdapter.verify_signature()` (static method)

```python
verify_signature(
    payload_body: bytes,
    signature: str,          # X-Hub-Signature-256 header
    app_secret: str,         # tenant's whatsapp_app_secret
    timestamp: str | None,   # optional, for replay protection
    max_age_seconds: int,    # default 300 (5 minutes)
)
```

1. Compute HMAC-SHA256 of the payload body using the app secret.
2. Compare with the `sha256=...` prefix in the signature header using `hmac.compare_digest` (timing-safe).
3. **Replay protection:** If a timestamp is provided, reject if older than `max_age_seconds`.

### Webhook Endpoint

**File:** `drivers/api/webhooks/whatsapp.py`

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/webhooks/{tenant_id}/whatsapp` | GET | Meta verification challenge (hub.mode + hub.verify_token + hub.challenge) |
| `/webhooks/{tenant_id}/whatsapp` | POST | Receive messages; verify signature, call `chat_with_agent`, send reply |

---

## Telegram Adapter

**File:** `infrastructure/channels/telegram.py` -- `TelegramAdapter`

Uses the Telegram Bot API. Each tenant has its own bot token stored in `TenantConfig.telegram_bot_token`.

### Incoming Message Parsing

Extracts from the Telegram update payload:

```text
message.from.id        → telegram_user_id (stored in metadata)
message.chat.id        → chat_id (used as sender_phone / recipient)
message.text           → text content
message.voice.file_id  → voice message (resolved to download URL)
message.photo[-1]      → highest-resolution photo (resolved to download URL)
```

File URLs are resolved via `GET /getFile?file_id=...` -> `https://api.telegram.org/file/bot{token}/{file_path}`.

### Outbound Sends

| Method | Telegram API method | Notes |
| ------ | ------------------- | ----- |
| `send_text` | `sendMessage` | HTML parse_mode; falls back to plain text on 400 |
| `send_image` | `sendPhoto` | URL-based, caption with HTML |
| `send_media_group` | `sendMediaGroup` | Native album API; falls back to plain caption on 400 |
| `send_video` | `sendVideo` | URL-based, caption with HTML |
| `send_document` | `sendDocument` | URL-based, caption with HTML |
| `send_voice` | `sendVoice` | File upload (multipart) |
| `send_contact_request` | `sendMessage` | Keyboard button with `request_contact: true` |

**Text chunking:** Messages are auto-chunked at 4096 characters (Telegram's limit). Each chunk is sent as a separate message.

**HTML fallback:** If Telegram rejects an HTML-formatted message (400 error), the adapter strips HTML tags and retries with plain text.

**Contact request flow:** When a Telegram user hasn't shared their phone number, the adapter can send a keyboard button prompting them to share. This is used during sender resolution when the `telegram_phones` table has no phone for the user.

### Webhook Endpoint

**File:** `drivers/api/webhooks/telegram.py`

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/webhooks/{tenant_id}/telegram` | POST | Receive updates; verify `X-Telegram-Bot-Api-Secret-Token` header against `TenantConfig.telegram_webhook_secret`, call `chat_with_agent`, send reply |

---

## Chat API (Direct)

**File:** `drivers/api/webhooks/chat_api.py`

Authenticated endpoint for testing the agent without channel webhooks.

| Endpoint | Method | Auth | Purpose |
| -------- | ------ | ---- | ------- |
| `/api/v1/chat` | POST | Bearer JWT | Send a test message through the full agent pipeline |

The endpoint resolves the tenant from the authenticated user's `user_tenants` membership and uses `ConversationChannel.API` as the channel. The sender identifier is the user's email.

---

## Contact Resolution Flow

Contact resolution happens **before** any message is saved, so every message in the DB has a real `participant_id` (or `None` for unresolved Telegram users).

**File:** `ai/utils/sender.py` -- `resolve_sender()`

### WhatsApp

```text
sender_phone (from webhook payload)
    │
    ▼
uow.contacts.get_or_create_by_phone(tenant_id, phone)
    │
    ▼
Contact.id   ← returned to gateway
```

Phone is the natural key. `get_or_create_by_phone` uses `INSERT ON CONFLICT` for `(tenant_id, phone)` uniqueness -- duplicate webhooks are safe.

### Telegram

```text
telegram_user_id (from webhook payload)
    │
    ▼
uow.telegram_phones.get_or_register(telegram_user_id)
    │
    ├── phone found → get_or_create_by_phone(tenant_id, phone)
    │                    └── contact.link_telegram(telegram_user_id)
    │                    └── Contact.id returned
    │
    └── no phone → None returned (user hasn't shared phone yet)
                   Messages still processed, but participant_id is NULL
```

The `telegram_phones` table maps `telegram_user_id` -> `phone`. When a user shares their phone via the contact request keyboard button, the mapping is stored and future messages resolve normally.

### API / Web

```text
sender_identifier (email or other identifier)
    │
    ▼
uow.contacts.get_or_create_by_phone(tenant_id, identifier)
    │
    ▼
Contact.id   ← returned to gateway
```

Treats the identifier as a phone-like key -- same upsert flow.

---

## Notification Routing


Channel-agnostic outbound notification routing. Given a tenant + recipient, resolves the best delivery channel.

### Resolution Fallback Chain

```text
resolve_route(tenant_id, recipient_id, recipient_type)
    │
    ├── Step 1: Find most recent conversation for this recipient+tenant
    │           → send to that conversation's channel + thread_id
    │
    ├── Step 2: Tenant has WhatsApp configured (phone_number_id + access_token)
    │           + recipient has a phone number
    │           → create a WhatsApp thread_id: "contact:{tenant_id}:{phone}:whatsapp"
    │
    ├── Step 3: Recipient has a telegram_user_id
    │           → create a Telegram thread_id: "contact:{tenant_id}:{tg_id}:telegram"
    │
    └── Step 4: All failed
```

**Returns:** `ResolvedRoute(channel, thread_id, conversation_id, tenant_id, recipient_id)`

**Recipient types:** Supports both `"contact"` (external people) and `"owner"/"user"` (internal users). Loads phone + telegram_user_id from the appropriate model (ContactModel or UserModel).

### Channel Delivery


Takes a `RecipientInfo`, message text, channel name, and tenant config. Uses the cached adapter pool (`infrastructure/channels/cache.py`) for connection reuse:

- **WhatsApp:** `get_whatsapp_adapter(tid, phone_number_id, access_token)` -> `wa.send_text(phone, message)`
- **Telegram:** `get_telegram_adapter(tid, tenant_config)` -> `tg.send_text(recipient, message)`

Returns `True` if delivered, `False` otherwise (logged, not raised).

---

## Retry Infrastructure

**File:** `infrastructure/channels/retry.py`

All channel sends use the `@channel_send_retry()` decorator for transient failure handling. Configurable parameters:

| Setting | Default | Purpose |
| ------- | ------- | ------- |
| `WHATSAPP_IMAGE_SEND_DELAY_SECONDS` | configurable | Delay between sequential image sends (WhatsApp albums) |
| `WHATSAPP_MAX_IMAGES_PER_ALBUM` | configurable | Max images per album send |

---

## Webhook Security Summary

| Channel | Verification Method | Header |
| ------- | ------------------- | ------ |
| WhatsApp | HMAC-SHA256 + optional replay protection | `X-Hub-Signature-256` |
| Telegram | Secret token comparison | `X-Telegram-Bot-Api-Secret-Token` |
| Chat API | JWT Bearer token (standard auth) | `Authorization` |

All webhook credentials are per-tenant, stored in the `tenant_configs` table, and loaded from the DB at request time.

---

## Key Source Files

| File | Role |
| ---- | ---- |
| `infrastructure/channels/base.py` | `ChannelAdapter` ABC, `IncomingMessage`, `OutgoingMessage`, media extraction pipeline |
| `infrastructure/channels/whatsapp.py` | `WhatsAppAdapter` -- Meta Cloud API v23.0 |
| `infrastructure/channels/telegram.py` | `TelegramAdapter` -- Telegram Bot API |
| `infrastructure/channels/cache.py` | Adapter caching for connection reuse |
| `infrastructure/channels/retry.py` | `@channel_send_retry()` decorator, configurable delays |
| `drivers/api/webhooks/whatsapp.py` | WhatsApp webhook endpoints (GET verify + POST receive) |
| `drivers/api/webhooks/telegram.py` | Telegram webhook endpoint (POST receive) |
| `drivers/api/webhooks/chat_api.py` | Direct chat API endpoint (POST, authenticated) |
| `ai/utils/sender.py` | `resolve_sender()` -- channel user -> Contact entity |
| `domain/shared/media.py` | `extract_media()` -- parse media blocks from LLM responses |
| `domain/shared/channel_result.py` | `ChannelSendResult` value object |
