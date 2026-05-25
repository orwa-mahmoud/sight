# Handover — Before Completing Any Task

## Checklist (MUST pass before declaring done)

### Backend
```bash
cd backend
uv run ruff check src/ tests/           # 0 errors
uv run ruff format --check src/ tests/   # 0 changes
uv run mypy src/                         # 0 errors (strict)
uv run pytest --tb=short -q --cov=src    # all pass, 90%+
```

### Frontend
```bash
cd frontend
npm run lint                             # 0 errors
npm run typecheck                        # 0 errors
npm test                                 # all pass
npm run build                            # succeeds
```

### SonarQube (BOTH projects must be 0/0/0)
```bash
export SONAR_TOKEN=$SONAR_TOKEN
export SONAR_USER_TOKEN=$SONAR_USER_TOKEN

# Backend scan
cd backend
uv run pytest --cov=src --cov-report=xml -q
sonar-scanner -Dsonar.host.url=http://localhost:9000

# Frontend scan
cd frontend
sonar-scanner -Dsonar.host.url=http://localhost:9000

# Wait 15s then verify
sleep 15
curl -s -u "$SONAR_USER_TOKEN:" "http://localhost:9000/api/measures/component?component=frontdesk-backend&metricKeys=bugs,vulnerabilities,code_smells,coverage" | python3 -c "import sys,json; d=json.load(sys.stdin); m={x['metric']:x['value'] for x in d['component']['measures']}; [print(f'{k}: {v}') for k,v in sorted(m.items())]"
curl -s -u "$SONAR_USER_TOKEN:" "http://localhost:9000/api/measures/component?component=frontdesk-frontend&metricKeys=bugs,vulnerabilities,code_smells" | python3 -c "import sys,json; d=json.load(sys.stdin); m={x['metric']:x['value'] for x in d['component']['measures']}; [print(f'{k}: {v}') for k,v in sorted(m.items())]"
```

**ALL must show 0 bugs, 0 vulnerabilities, 0 code smells.**

### Server verification
```bash
cd backend
uv run uvicorn src.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/openapi.json | python3 -c "import sys,json; paths=json.load(sys.stdin)['paths']; print(f'{len(paths)} routes')"
kill %1
```

### DDD layer audit (must return EMPTY)
```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" backend/src/application/
grep -rn "^from langchain\|^from langgraph" backend/src/domain/ backend/src/application/
```

## Current State (as of last session)

Run these to get current numbers:

```bash
git log --oneline | wc -l                                    # commits
cd backend && uv run pytest --tb=short -q --cov=src 2>&1 | tail -3  # tests + coverage
cd frontend && npx vitest run 2>&1 | grep Tests              # frontend tests
```

- **SonarQube:** 0/0/0 on BOTH projects, quality gates PASSED
- **CI:** GitHub Actions on PRs only, Husky pre-commit hooks, branch protection on main
- **LangGraph StateGraph** wired for per-turn orchestration
- **DB messages** as cross-turn source of truth (no LangGraph checkpointer)
- **Per-tenant LLM config** from tenant_configs table (not .env)

## What's working

- Auth (register + login + JWT + /me)
- Per-tenant config (LLM, WhatsApp, Telegram, bot personality)
- Settings UI (frontend accordion page)
- RAG (pgvector HNSW + tsvector GIN + RRF hybrid retrieval)
- Document upload + ingestion + retrieval
- Escalation system (Question state machine + inbox UI)
- Agent loop (LangGraph graph → search_documents + escalate_question + save_key_fact)
- Token/cost ledger
- Conversations list + daily summary
- Chat test page (frontend)
- WhatsApp + Telegram webhooks
- Key facts (persistent per-asker memory)
- Circuit breaker + error classifier
- Event bus (blinker) + event handlers
- Domain event outbox
- Prometheus metrics + /metrics endpoint
- Docker Compose + Dockerfiles
- GitHub Actions CI
- Request ID middleware

## What needs live API key to test

- Actual LLM responses (set OPENAI_API_KEY via Settings → LLM)
- Document embedding (set embedding API key via Settings → Embedding)
- WhatsApp/Telegram reply (set channel tokens via Settings)

## Architecture rules (NEVER break)

1. Domain has ZERO imports from application/infrastructure/drivers/ai
2. LangChain/LangGraph ONLY in infrastructure/llm/ and infrastructure/ai/
3. Never trust client-provided tenant_id — resolve from user_tenants
4. Never commit without running ALL checks above
5. Never push without explicit user approval
