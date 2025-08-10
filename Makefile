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
	poetry run pytest -c config/testing/pytest.ini --cov --cov-fail-under=60

ci: lint type test

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
