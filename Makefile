.DEFAULT_GOAL := help
.PHONY: help check check-backend check-frontend setup up down eval erd

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

check:  ## Run all CI gates locally (backend + frontend)
	./check.sh all

check-backend:  ## Backend gates only (ruff, mypy, pytest)
	./check.sh backend

check-frontend:  ## Frontend gates only (lint, typecheck, test)
	./check.sh frontend

setup:  ## Create .env.docker with generated secrets if missing
	@if [ ! -f .env.docker ]; then \
		cp .env.docker.example .env.docker; \
		JWT=$$(python3 -c "import secrets;print(secrets.token_urlsafe(48))"); \
		ENC=$$(python3 -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())" 2>/dev/null || python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"); \
		sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$$JWT|" .env.docker && rm -f .env.docker.bak; \
		sed -i.bak "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$$ENC|" .env.docker && rm -f .env.docker.bak; \
		echo "✅ wrote .env.docker with generated JWT_SECRET_KEY + ENCRYPTION_KEY"; \
	else echo ".env.docker already exists — leaving it alone"; fi

up:  ## docker compose up --build
	docker compose up --build

down:  ## docker compose down
	docker compose down

eval:  ## Run the RAG/agent eval harness (needs EVAL_LLM_API_KEY + EVAL_EMBEDDING_API_KEY)
	cd backend && uv run python -m eval.run

erd:  ## Regenerate backend/docs/erd.png from the live schema (needs system graphviz)
	cd backend && uv run --extra erd python scripts/generate_erd.py
