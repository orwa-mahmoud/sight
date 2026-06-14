#!/usr/bin/env bash
# Run every CI gate locally — backend (ruff, mypy, pytest) + frontend (lint,
# typecheck, test). Mirrors .github/workflows/ci.yml. Exits non-zero on first
# failure. Usage: ./check.sh [backend|frontend]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-all}"

run_backend() {
  echo "── backend ───────────────────────────────────────────"
  cd "$ROOT/backend"
  uv run ruff check src/ tests/
  uv run ruff format --check src/ tests/
  uv run mypy src/
  uv run pytest tests/ --tb=short -q
}

run_frontend() {
  echo "── frontend ──────────────────────────────────────────"
  cd "$ROOT/frontend"
  npm run lint
  npm run typecheck
  npm test
}

case "$TARGET" in
  backend)  run_backend ;;
  frontend) run_frontend ;;
  all)      run_backend; run_frontend ;;
  *) echo "usage: ./check.sh [backend|frontend|all]"; exit 2 ;;
esac

echo "✅ all checks passed"
