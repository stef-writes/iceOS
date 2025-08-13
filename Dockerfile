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
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG APP_USER=appuser
ARG APP_UID=10001
ARG APP_GID=10001
ARG VCS_REF="unknown"
ARG BUILD_DATE="unknown"
ARG VERSION="0.0.0"
ARG REPOSITORY=""

WORKDIR /app

# Create non-root user
RUN groupadd -g ${APP_GID} ${APP_USER} \
    && useradd -m -u ${APP_UID} -g ${APP_GID} -s /usr/sbin/nologin ${APP_USER}

# Install runtime dependencies
COPY --from=builder /tmp/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade "pip==24.1.2" \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# Copy application source and first-party packs (for plugin manifests)
COPY src /app/src
COPY packs /app/packs
ENV PYTHONPATH=/app/src

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
    ICE_STRICT_SERIALIZATION=1
ARG VCS_REF="unknown"
ARG BUILD_DATE="unknown"
ARG VERSION="0.0.0"
ARG REPOSITORY=""

WORKDIR /app

# Install dependencies exported from the lockfile (cached in image layers)
COPY --from=builder /tmp/requirements.txt /tmp/requirements.txt
COPY --from=builder /tmp/requirements-dev.txt /tmp/requirements-dev.txt
RUN python -m pip install --no-cache-dir --timeout 120 --retries 5 -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

# Copy application source and test config
COPY src /app/src
COPY config /app/config
COPY tests /app/tests
ENV PYTHONPATH=/app/src

# OCI labels
LABEL org.opencontainers.image.title="iceOS Test Runner" \
      org.opencontainers.image.description="Pytest runner image with dependencies" \
      org.opencontainers.image.source="https://github.com/${REPOSITORY}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"

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
      typing-extensions==4.12.2 types-PyYAML==6.0.12.20250516 types-redis==4.6.0.20241004

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
