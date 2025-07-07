# Makefile for iceOS – high-level dev tasks

PYTHON := $(shell which python)
PIP := pip

.PHONY: help install lint type test coverage mutation refresh-docs doctor clean docs deep-clean

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies (core + [test] extras)"
	@echo "  lint           Run ruff and isort checks"
	@echo "  type           Run mypy static type checking"
	@echo "  test           Run pytest with coverage"
	@echo "  coverage       Run pytest with branch coverage"
	@echo "  mutation       Run mutmut mutation testing"
	@echo "  refresh-docs   Regenerate docs (catalog + overview)"
	@echo "  doctor         Run full healthcheck suite"
	@echo "  clean          Remove .pyc, build, and coverage artifacts"
	@echo "  docs           Build documentation site (output to site/)"
	@echo "  deep-clean     Remove build/test artifacts, caches, logs, compiled files and local data"

install:
	poetry install --with dev --no-interaction --no-root

lint:
	poetry run ruff check src
	poetry run isort --check-only src
	poetry run mypy src

format:
	poetry run black src scripts tests
	poetry run isort src scripts tests

type:
	poetry run mypy src

test:
	poetry run pytest -q

refresh-docs:
	$(PYTHON) scripts/gen_catalog.py
	$(PYTHON) scripts/gen_overview.py

# Robust quoting so paths with spaces/parentheses do not break ----------------
doctor:
	poetry run "$(PYTHON)" scripts/doctor.py

coverage:
	poetry run pytest

mutation:
	poetry run mutmut run --paths-to-mutate src --tests-dir tests

clean:
	rm -rf .pytest_cache dist build *.egg-info
	rm -rf .coverage htmlcov .ruff_cache .mypy_cache .benchmarks .import_linter_cache .hypothesis
	rm -rf logs *.log data/*.db data/*.sqlite3 data/context_store.json
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.py[co]" -delete

docs:
	mkdocs build -s 

# Deep clean also removes virtual environment & compiled docs
deep-clean: clean
	rm -rf .venv venv ENV
	rm -rf site
	rm -rf docs/generated 