FROM python:3.11-slim

# -- Poetry ---------------------------------------------------------------
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PATH="${POETRY_HOME}/bin:${PATH}"

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
ENV PYTHONPATH=/app/src

# Expose default FastAPI port
EXPOSE 8000

# Launch the API server
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "5", "--limit-concurrency", "100"] 