# Frontdesk — Business Overview

## What Is Frontdesk?

Frontdesk is a **multi-tenant AI front desk assistant** that answers questions on a business owner's behalf. Each tenant (business) uploads documents to a knowledge base, and an AI agent uses those documents to answer incoming questions from visitors on WhatsApp, Telegram, or a direct API. Anything the AI cannot answer is escalated to the business owner, who replies from a web dashboard.

Each business gets its own isolated assistant with independent LLM credentials, channel integrations, and knowledge base. The platform is built for **multi-tenant SaaS** — one deployment serves unlimited businesses.

---

## The Problem

Small businesses and service providers lose inquiries and waste time because:

- **Repetitive questions** — owners answer the same "What are your hours?", "How much does X cost?", "Do you offer Y?" dozens of times a week across multiple channels.
- **Slow response times** — visitors message on WhatsApp at night, nobody replies until the next day. By then, they have moved on.
- **No visibility** — owners cannot see what questions are being asked, what the AI answered, or where it failed.
- **Channel fragmentation** — questions arrive on WhatsApp, Telegram, and the web with no unified view.

## The Solution

Frontdesk automates the first line of response:

1. **Visitor sends a question** (WhatsApp, Telegram, or web chat)
2. **The AI searches the knowledge base** — uploaded documents are chunked, embedded, and indexed for hybrid retrieval (vector + BM25)
3. **If found, it answers** — grounded in the actual documents, not hallucinated
4. **If not found, it escalates** — creates a pending question for the owner with the AI's failed answer attempt and the visitor's contact info
5. **Owner replies from the dashboard** — the reply is relayed back to the visitor's original channel

---

## Core Features

### 1. AI-Powered Conversations

The assistant is not a scripted chatbot. It understands natural language, searches the knowledge base, and answers based on what it finds. If it cannot find a confident answer, it escalates rather than guessing.

- Always searches documents before answering
- Answers in 1-3 sentences, matching the visitor's language
- Remembers key facts about returning visitors (name, preferences) across sessions
- Escalates immediately if the visitor asks to speak with a person

**Business value:** Visitors get instant, accurate responses 24/7. No question goes unanswered.

### 2. Multi-Channel Support

Businesses meet visitors where they already are:

- **WhatsApp** — Meta Cloud API integration with signature verification and rich media support
- **Telegram** — Bot API with phone number resolution for contact identity
- **Direct API** — REST endpoint for embedding chat on websites or custom integrations
- **In-dashboard test console** — owners chat with their own assistant directly in the
  dashboard (runs the full agent pipeline as the `api` channel), so they can verify how
  the AI answers from their uploaded documents without configuring WhatsApp or Telegram
  first. The view shows the retrieved source documents, escalation status, response
  latency, and per-reply token usage.

Each channel maintains its own conversation thread. The AI has long-term memory per contact, so preferences carry across sessions regardless of channel.

**Business value:** One assistant covers all visitor touchpoints — and owners can test it end-to-end before going live.

### 3. Knowledge Base (RAG)

Owners upload documents (PDF, DOCX, Markdown, plain text) to build the AI's knowledge. The ingestion pipeline:

1. Parses the document into raw text
2. Chunks into ~512-token windows with 15% overlap
3. Embeds with OpenAI `text-embedding-3-large` (1536 dims)
4. Indexes with pgvector HNSW for vector search and Postgres GIN for BM25 keyword search

At query time, both indexes are searched and results are combined via Reciprocal Rank Fusion (RRF) for high-quality retrieval.

**Business value:** Better documents = better answers = fewer escalations.

### 4. Escalation Inbox

When the AI cannot answer a question, it creates a `Question` entity with full lifecycle tracking:

| Step | What Happens |
| ---- | ------------ |
| **Escalation** | AI determines it cannot answer confidently. Creates a question with the visitor's text and its own failed answer attempt. |
| **Dashboard notification** | Owner sees the new question in the inbox with the contact info and conversation context. |
| **Reply** | Owner writes a reply from the dashboard. |
| **Relay** | The reply is sent back to the visitor on their original channel. |
| **Close** | Questions can be closed without a reply if they are irrelevant. |

**Status flow:** Submitted -> Resolved (replied) | Closed (dismissed)

**Business value:** No question falls through the cracks. Owners see exactly why an escalation happened and can respond efficiently.

### 5. Key Facts Memory

The AI remembers facts about returning visitors — their name, preferences, past topics — and uses them to personalize future conversations. Owners can view and manage stored facts from the dashboard.

**Business value:** Returning visitors feel recognized. The AI gets better with each interaction.

### 6. Cost Accountability

Every LLM call is tracked with provider, model, token counts, and cost in `Decimal(18,8)` precision. The dashboard shows a token usage ledger with cost breakdown by time period.

**Business value:** Full transparency on AI costs per tenant, per conversation, per request.

### 7. Multi-Tenant Architecture

Each business operates in complete isolation:

| Capability | Per-Tenant |
| ---------- | ---------- |
| **Data** | Contacts, conversations, documents, questions, key facts — fully isolated |
| **AI Model** | Choose provider (OpenAI, Anthropic, Google Gemini) and model — each business brings its own API key |
| **Embedding** | Own embedding provider, model, and dimensions |
| **Bot Personality** | Custom name, welcome message, and language |
| **Channels** | Own WhatsApp number, own Telegram bot |

**Business value:** Sell to unlimited businesses from one deployment. Each business feels like they have their own product.

---

## How It Works (End to End)

```
Owner signs up -> Creates tenant -> Configures LLM + embedding API keys
                                  -> Uploads documents to knowledge base
                                  -> Connects WhatsApp / Telegram

Visitor messages on WhatsApp
    -> AI greets, asks how it can help
    -> Visitor: "What are your opening hours?"
    -> AI searches knowledge base, finds the answer in uploaded docs
    -> AI responds: "We're open Monday-Friday 9am-6pm and Saturday 10am-2pm."

Visitor messages: "How much does the premium plan cost?"
    -> AI searches knowledge base, no confident result found
    -> AI escalates: "Let me check with the team and get back to you."
    -> Owner sees escalation in dashboard inbox
    -> Owner replies: "The premium plan is $99/month with a 14-day free trial."
    -> Visitor receives the reply on WhatsApp

Visitor messages again next week
    -> AI loads key facts: "Known: name is Ahmed, asked about premium plan last week"
    -> AI provides context-aware, personalized response
```

---

## Target Users

- **Primary:** Small-to-medium businesses (services, clinics, agencies, consultancies) that receive repetitive questions across WhatsApp and Telegram
- **Secondary:** Any organization that needs a document-grounded AI assistant with human escalation and full audit trail
