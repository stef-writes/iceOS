# Makefile for iceOS – high-level dev tasks

PYTHON := $(shell which python)
PIP := pip

.PHONY: help install lint type test coverage mutation refresh-docs doctor clean docs deep-clean lock-check

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies (core + [test] extras)"
	@echo "  lint           Run ruff and isort checks"
	@echo "  type           Run MyPy (--strict) type checking"
	@echo "  test           Run pytest with coverage"
	@echo "  coverage       Run pytest with branch coverage"
	@echo "  mutation       Run mutmut mutation testing"
	@echo "  refresh-docs   Regenerate docs (catalog + overview)"
	@echo "  doctor         Run full healthcheck suite"
	@echo "  clean          Remove .pyc, build, and coverage artifacts"
	@echo "  docs           Build documentation site (output to site/)"
	@echo "  deep-clean     Remove build/test artifacts, caches, logs, compiled files and local data"
	@echo "  lock-check     Check if dependencies are locked"

install:
	poetry install --with dev --no-interaction

# Linting
lint:
	poetry run ice doctor lint

format:
	poetry run black src scripts tests
	poetry run isort src scripts tests

# Type checking
type:
	# Strict type checking for modernised layers (app + core)
	poetry run mypy --strict --config-file mypy.ini src/ice_api src/ice_core src/ice_sdk/utils src/ice_sdk/context src/ice_sdk/tools src/ice_sdk/extensions src/ice_sdk/executors src/ice_sdk/dsl src/ice_sdk/agents src/ice_sdk/providers
	poetry run mypy --strict --config-file mypy.ini src/ice_orchestrator

typecheck: type  # alias for docs compatibility

# Testing
test:
	poetry run ice doctor test

refresh-docs:
	$(PYTHON) scripts/gen_catalog.py
	$(PYTHON) scripts/gen_overview.py

# Comprehensive quality gate (lint + type + test + optional perf)
doctor:
	poetry run ice doctor all
	poetry run pre-commit run --all-files --show-diff-on-failure
	$(PYTHON) scripts/check_layers.py

# Architectural guard – run by CI and pre-commit
structure:
	$(PYTHON) scripts/check_layers.py

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

lock-check:
	poetry lock --no-interaction 

# Robust production gate (lint, deps, tests, security)
production-check:
	poetry run ruff check --strict --diff .
	poetry run import-linter --config .importlinter
	poetry run pytest --cov --cov-fail-under=90
	poetry run pip-audit
	git-secrets --scan 