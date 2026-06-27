FROM python:3.13-slim

# Run as a non-root user (defense in depth: a compromised process has no root).
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# The app imports `src.*` directly and is run from /app, so it doesn't need to
# be installed as a package — only its dependencies. PYTHONPATH makes `src`
# importable at runtime without an editable install.
ENV PYTHONPATH=/app

RUN pip install uv

COPY pyproject.toml uv.lock ./
# Install dependencies only. --no-install-project skips building the `sight`
# package itself, which references ../README.md (outside this build context) and
# whose source (src/) isn't copied until the next layer.
RUN uv sync --no-dev --frozen --no-install-project

COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/
COPY docker-entrypoint.sh ./

# Create the upload dir owned by appuser BEFORE the named volume mounts over it:
# Docker seeds a fresh named volume from the mount point's ownership, so this keeps
# uploads writable by the non-root user (otherwise the volume defaults to root).
RUN mkdir -p /app/var/uploads && chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Entrypoint runs migrations, then execs CMD.
# --no-sync: the venv is already built; don't re-resolve (which would try to
# build the uninstalled project and fail on the out-of-context README).
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uv", "run", "--no-sync", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
