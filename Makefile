# Makefile for iceOS – minimal developer tasks

PYTHON := $(shell which python)

.PHONY: install lint format type test ci clean serve stop-serve dev

install:
	poetry install --with dev --no-interaction

lint:
	poetry run ruff check src tests
	poetry run isort --check-only src tests

format:
	poetry run black src tests
	poetry run isort src tests

type:
	poetry run mypy --strict src

test:
	poetry run pytest -c config/testing/pytest.ini --cov --cov-fail-under=55

ci: lint type test

# ---------------------------------------------------------------------------
# Dev server helpers --------------------------------------------------------
# ---------------------------------------------------------------------------
serve:
	PYTHONPATH=src uvicorn ice_api.main:app --port 8000 --reload

dev: serve

stop-serve:
	- lsof -ti tcp:8000 | xargs kill -9 || true

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	 rm -rf .ruff_cache .mypy_cache .pytest_cache htmlcov .coverage
