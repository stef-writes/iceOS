# Makefile for iceOS – minimal developer tasks

PYTHON := $(shell which python)

.PHONY: install lint format format-check audit type test ci clean serve stop-serve dev

install:
	poetry install --with dev --no-interaction

lint:
	poetry run ruff check src tests
	poetry run isort --check-only src tests

format:
	poetry run isort src tests
	poetry run black src tests

format-check:
	poetry run isort --check-only src tests
	poetry run black --check src tests

type:
	poetry run mypy --config-file config/typing/mypy.ini src

test:
	poetry run pytest -c config/testing/pytest.ini --cov --cov-fail-under=60 -k "not integration"

ci: lint type test
	# Run integration tests only when redis and testcontainers are present
	@if poetry run python -c "import importlib; import sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ['redis.asyncio','testcontainers']) else 1)"; then \
		poetry run pytest -c config/testing/pytest.ini tests/integration --cov --cov-append; \
	else \
		echo "Skipping integration tests: redis/testcontainers not installed"; \
	fi

audit:
	poetry run pip-audit || true

# ---------------------------------------------------------------------------
# Dev server helpers --------------------------------------------------------
# ---------------------------------------------------------------------------
serve:
	PYTHONPATH=src uvicorn ice_api.main:app --port 8000 --reload

dev: serve

# Live verification (real LLM + SerpAPI if keys present)
verify-live:
	OPENAI_API_KEY=$$OPENAI_API_KEY SERPAPI_KEY=$$SERPAPI_KEY poetry run python scripts/verify_runtime.py

stop-serve:
	- lsof -ti tcp:8000 | xargs kill -9 || true

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	 rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage

# Zero-setup dev server (no Docker, in-memory Redis stub)
.PHONY: dev-zero
dev-zero:
	USE_FAKE_REDIS=1 PYTHONPATH=src uvicorn ice_api.main:app --port 8000 --reload
