# Handover — Verification Checklist

Run all of these before declaring any task done.
Architecture rules and conventions are in [CLAUDE.md](../CLAUDE.md) and
the subproject CLAUDE.md files — not repeated here.

## Backend
```bash
cd backend
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest --tb=short -q --cov=src
```

## Frontend
```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## SonarQube (both projects must be 0/0/0)
```bash
cd backend
uv run pytest --cov=src --cov-report=xml -q
sonar-scanner -Dsonar.host.url=http://localhost:9000

cd frontend
sonar-scanner -Dsonar.host.url=http://localhost:9000
```

## DDD layer audit (must return empty)
```bash
grep -rn "^from src\.\(infrastructure\|drivers\|ai\)" backend/src/application/
grep -rn "^from langchain\|^from langgraph" backend/src/domain/ backend/src/application/
```
