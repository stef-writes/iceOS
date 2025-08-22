FROM python:3.11.9-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3

WORKDIR /app

# Install Poetry to export a deterministic requirements.txt from the lockfile
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock /app/

# Export dependencies with enforced extras for runtime (WASM, DB, LLM providers)
# DeepSeek is OpenAI-compatible and piggybacks on openai client
RUN poetry export -f requirements.txt --without-hashes \
    -E wasm -E database -E llm_openai -E llm_anthropic \
    -o /tmp/requirements.txt

# Also export a dev-inclusive requirements set for test stage caching
RUN poetry export -f requirements.txt --without-hashes --with dev -o /tmp/requirements-dev.txt


FROM python:3.11.9-slim AS api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src:/app

ARG APP_USER=appuser
ARG APP_UID=10001
ARG APP_GID=10001
ARG VCS_REF="unknown"
ARG BUILD_DATE="unknown"
ARG VERSION="0.0.0"
ARG REPOSITORY=""

WORKDIR /app

# Security updates for base OS packages (Debian) to reduce known CVEs
RUN apt-get update -qq \
    && apt-get -y dist-upgrade \
    && apt-get -y install --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g ${APP_GID} ${APP_USER} \
    && useradd -m -u ${APP_UID} -g ${APP_GID} -s /usr/sbin/nologin ${APP_USER}

# Install runtime dependencies
COPY --from=builder /tmp/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade "pip==24.1.2" \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# Rely solely on Poetry-exported requirements to avoid dependency drift

# Copy application source, migrations, and capability kits (for plugin manifests)
COPY src /app/src
COPY scripts /app/scripts
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY Plugins /app/plugins
COPY examples /app/examples
ENV PYTHONPATH=/app/src:/app

# Expose default FastAPI port
EXPOSE 8000

# OCI image labels for traceability
LABEL org.opencontainers.image.title="iceOS API" \
      org.opencontainers.image.description="iceOS FastAPI application image" \
      org.opencontainers.image.url="https://github.com/${REPOSITORY}" \
      org.opencontainers.image.source="https://github.com/${REPOSITORY}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"

# Drop privileges
USER ${APP_UID}:${APP_GID}

# Launch the API server
CMD ["uvicorn", "ice_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "5", "--limit-concurrency", "100"]

# ---------------------------------------------------------------------------
# Cached test stage: installs deps from lock and runs pytest without fetching
# ---------------------------------------------------------------------------
FROM python:3.11.9-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ICE_ENABLE_INLINE_CODE=1 \
    ICE_COMPUTE_GRAPH_CENTRALITY=1 \
    ICE_STRICT_SERIALIZATION=1 \
    PYTHONPATH=/app/src:/app
ARG VCS_REF="unknown"
ARG BUILD_DATE="unknown"
ARG VERSION="0.0.0"
ARG REPOSITORY=""

WORKDIR /app

# Security updates for base OS packages (Debian) to reduce known CVEs in test image
RUN apt-get update -qq \
    && apt-get -y dist-upgrade \
    && apt-get -y install --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies exported from the lockfile (cached in image layers)
COPY --from=builder /tmp/requirements.txt /tmp/requirements.txt
COPY --from=builder /tmp/requirements-dev.txt /tmp/requirements-dev.txt
# Avoid self-upgrading pip/setuptools from dev requirements to prevent hash/installer issues
RUN sed -i '/^pip==/d' /tmp/requirements-dev.txt && sed -i '/^setuptools==/d' /tmp/requirements-dev.txt
RUN python -m pip install --no-cache-dir --timeout 120 --retries 5 -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

# Keep test image aligned with lockfile; avoid ad-hoc upgrades or stubs that fight the plugin

# Copy application source and test config
COPY src /app/src
COPY Plugins /app/plugins
COPY scripts /app/scripts
COPY config /app/config
COPY tests /app/tests
COPY examples /app/examples
ENV PYTHONPATH=/app/src:/app

# OCI labels
LABEL org.opencontainers.image.title="iceOS Test Runner" \
      org.opencontainers.image.description="Pytest runner image with dependencies" \
      org.opencontainers.image.source="https://github.com/${REPOSITORY}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"

# Auto-register demo tools for pytest via sitecustomize in the same interpreter
RUN printf '%s\n' \
  'from ice_core.unified_registry import register_tool_factory' \
  'register_tool_factory("writer_tool", "plugins.kits.tools.search.writer_tool:create_writer_tool")' \
  > /usr/local/lib/python3.11/site-packages/sitecustomize.py

# Pre-test bootstrap: ensure required demo tools are registered in this process.
# Keep this minimal and deterministic; avoid external APIs/keys.
RUN printf '%s\n' \
  '#!/usr/bin/env sh' \
  'set -eu' \
  "python - <<'PY'" \
  'from ice_core.unified_registry import register_tool_factory' \
  'import importlib' \
  'try:' \
  '    importlib.import_module("plugins.kits.tools.search.writer_tool")' \
  'except Exception as e:' \
  '    raise SystemExit(f"bootstrap: failed to import writer_tool: {e}")' \
  'register_tool_factory("writer_tool", "plugins.kits.tools.search.writer_tool:create_writer_tool")' \
  'print("bootstrap: writer_tool registered")' \
  'PY' \
  > /usr/local/bin/itest-bootstrap && chmod +x /usr/local/bin/itest-bootstrap

# Default command (can be overridden at docker run)
CMD ["pytest", "-c", "config/testing/pytest.ini", "tests/unit", "-q"]

# ---------------------------------------------------------------------------
# Optional dev-check stage to run type checks in Docker identically to CI
# Build and run with:
#   docker build --target devcheck -t iceos-devcheck .
#   docker run --rm iceos-devcheck
# ---------------------------------------------------------------------------
FROM python:3.11.9-slim AS devcheck

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
ARG VCS_REF="unknown"
ARG BUILD_DATE="unknown"
ARG VERSION="0.0.0"
ARG REPOSITORY=""

WORKDIR /app

RUN python -m pip install --no-cache-dir \
      mypy==1.10.0 pydantic==2.8.2 pydantic-core==2.20.1 \
      typing-extensions==4.12.2 types-PyYAML==6.0.12.20250516 types-redis==4.6.0.20241004 \
      sqlalchemy==2.0.32

COPY src /app/src
COPY config /app/config
COPY typings /app/typings

LABEL org.opencontainers.image.title="iceOS Devcheck" \
      org.opencontainers.image.description="Dockerized mypy type-check stage" \
      org.opencontainers.image.source="https://github.com/${REPOSITORY}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"

CMD ["mypy", "--config-file", "config/typing/mypy.ini", "src"]

# ---------------------------------------------------------------------------
# Default final stage to ensure non-targeted builds produce the API image
# ---------------------------------------------------------------------------
FROM api AS final
