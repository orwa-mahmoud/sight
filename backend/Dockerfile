FROM python:3.13-slim

# Run as a non-root user (defense in depth: a compromised process has no root).
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/
COPY docker-entrypoint.sh ./

RUN chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Entrypoint runs migrations, then execs CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
