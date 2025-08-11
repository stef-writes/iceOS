FROM python:3.11-slim

# -- Poetry ---------------------------------------------------------------
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="${POETRY_HOME}/bin:${PATH}"

ARG APP_USER=appuser
ARG APP_UID=10001
ARG APP_GID=10001

# Create non-root user
RUN groupadd -g ${APP_GID} ${APP_USER} \
    && useradd -m -u ${APP_UID} -g ${APP_GID} -s /usr/sbin/nologin ${APP_USER}

# Working directory
WORKDIR /app

# Install Poetry first (frozen version)
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Install dependencies (cached layer)
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root --only main --no-interaction --no-ansi \
 && poetry cache clear --all pypi

# Copy application source
COPY src /app/src
# PYTHONPATH includes src so iceos_api is importable
ENV PYTHONPATH=/app/src

# Expose default FastAPI port
EXPOSE 8000

# Drop privileges
USER ${APP_UID}:${APP_GID}

# Launch the API server
CMD ["poetry", "run", "uvicorn", "ice_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "5", "--limit-concurrency", "100"]
