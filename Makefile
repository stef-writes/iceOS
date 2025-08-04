# Makefile for iceOS – high-level dev tasks

PYTHON := $(shell which python)
PIP := pip

.PHONY: help install lint type test coverage mutation refresh-docs doctor clean docs deep-clean lock-check dev run-demo
.PHONY: setup typecheck ci

help:
	@echo "Available targets:"
	@echo "  install        Install dependencies (core + [test] extras)"
	@echo "  lint           Run ruff and isort checks"
	@echo "  type           Run MyPy (--strict) type checking"
	@echo "  test           Run pytest with coverage"
	@echo "  coverage       Run pytest with branch coverage"
	@echo "  mutation       Run mutmut mutation testing"
	@echo "  refresh-docs   Regenerate docs (catalog + overview + layout + CLI)"
	@echo "  doctor         Run full healthcheck suite"
	@echo "  setup          One-shot bootstrap: install deps, git hooks"
	@echo "  ci             Lint, type-check, tests, security audit (what CI runs)"
	@echo "  clean          Remove .pyc, build, and coverage artifacts"
	@echo "  docs           Build documentation site (output to site/)"
	@echo "  deep-clean     Remove build/test artifacts, caches, logs, compiled files and local data"
	@echo "  lock-check     Check if dependencies are locked"

install:
	poetry install --with dev --no-interaction

# Idempotent first-time setup ------------------------------------------------

setup: install
	@echo "Installing pre-commit hooks …"
	poetry run pre-commit install --install-hooks --overwrite
	@echo "Setup complete ✔"

# Linting
lint:
	poetry run ruff check --config config/linting/ruff.toml --diff .
	poetry run isort --check-only src scripts tests

format:
	poetry run black src scripts tests
	poetry run isort src scripts tests

# Type checking
type:
	# Strict type checking for modernised layers (app + core)
	poetry run mypy --strict --config-file config/typing/mypy.ini src/ice_api src/ice_core src/ice_builder src/ice_client
	poetry run mypy --strict --config-file config/typing/mypy.ini src/ice_orchestrator


typecheck: type  # alias for docs compatibility

# Testing
test:
	$(PYTHON) scripts/check_layers.py
	poetry run pytest -c config/testing/pytest.ini

refresh-docs:
	$(PYTHON) scripts/gen_catalog.py
	$(PYTHON) scripts/gen_overview.py
	$(PYTHON) scripts/gen_repo_layout.py
	$(PYTHON) scripts/gen_cli_overview.py

# Comprehensive quality gate (lint + type + test)
# (Uses local venv; bootstrap via `make dev` first.)
doctor:
	.venv/bin/ruff check --config config/linting/ruff.toml .
	.venv/bin/mypy --strict --config-file config/typing/mypy.ini src/ice_api src/ice_core src/ice_orchestrator
	.venv/bin/pytest -c config/testing/pytest.ini -q

# Architectural guard – run by CI and pre-commit
structure:
	"$(PYTHON)" scripts/check_layers.py
	"$(PYTHON)" scripts/ci/check_aliases.py
	"$(PYTHON)" scripts/ci/check_input_literals.py

coverage:
	poetry run pytest -c config/testing/pytest.ini

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
	poetry run ruff check --config config/linting/ruff.toml --diff .
	poetry run lint-imports --config config/.importlinter
	poetry run pytest -c config/testing/pytest.ini --cov --cov-fail-under=60
	poetry run pip-audit
	git-secrets --scan 

audit-deps:
	poetry run pip-audit --summary
	poetry run pip-licenses --format=plain --with-authors --with-urls

audit:
	python -m scripts.check_layer_violations
	python -m scripts.check_service_contracts
	python -m scripts.validate_decision_records
	pytest -c config/testing/pytest.ini tests/unit/lint -v 

# ---------------------------------------------------------------------------
# Local development helpers --------------------------------------------------
# ---------------------------------------------------------------------------

dev: ## Start Redis & API server with hot-reload (foreground)
	@echo "Checking Redis availability..."; \
	if ! lsof -i :6379 > /dev/null 2>&1; then \
		echo "Starting Redis via Docker..."; \
		docker compose up -d redis; \
		until docker compose exec redis redis-cli ping | grep -q PONG; do sleep 1; done; \
	else \
		echo "Redis already running on port 6379"; \
	fi
	@echo "Starting API server with Poetry (hot-reload)…"
	poetry run uvicorn ice_api.main:app --reload --host 0.0.0.0 --port 8000

# One-liner background startup – convenience for demo users
# Writes API PID to .dev_api_pid so `make dev-down` can stop it.
dev-up: ## Start Redis & API (background) for CLI demos
	@echo "[dev-up] Bringing up Redis container…"; \
	if ! docker compose ps redis | grep -q "Up"; then \
		docker compose up -d redis; \
	fi;
	@echo "[dev-up] Starting API server in background…"; \
	poetry run uvicorn ice_api.main:app --host 0.0.0.0 --port 8000 > logs/dev_api.log 2>&1 & echo $$! > .dev_api_pid; \
	echo "API PID=$$(cat .dev_api_pid) (logs -> logs/dev_api.log)";

# Tear down background API + optional Redis container
.dev_stop:
	@echo "[dev-down] Stopping background API if running…"; \
	if [ -f .dev_api_pid ] && kill -0 $$(cat .dev_api_pid) 2>/dev/null; then \
		kill $$(cat .dev_api_pid) && rm .dev_api_pid; \
	fi;

dev-down: .dev_stop ## Stop API started by dev-up
	@echo "[dev-down] Done."

run-demo: ## Execute CSV→Summary demo (requires dev server running)
	.venv/bin/python examples/comprehensive_demo_example.py \
		--csv examples/items.csv --base-url http://localhost:8000 

# ---------------------------------------------------------------------------
# Continuous-integration gate (mirrors GitHub Actions) -----------------------
# ---------------------------------------------------------------------------

ci: lint type test structure
	poetry run pip-audit --summary

# ---------------------------------------------------------------------------
# Release candidate build ----------------------------------------------------
# ---------------------------------------------------------------------------
#   1. Ensure lockfile is fresh & deps pinned
#   2. Run full quality gate (ci)
#   3. Regenerate docs & schemas; fail if drift
#   4. Build Docker image for smoke testing
#
# Usage: `make release-candidate`
# ---------------------------------------------------------------------------

release-candidate: lock-check refresh-docs
	$(PYTHON) scripts/gen_docs/build_all.py
	$(PYTHON) scripts/ci/check_schema_drift.py
	$(MAKE) ci
	$(MAKE) audit-deps
	docker build -t iceos:rc .
	@echo "[release-candidate] Docker image tag 'iceos:rc' built successfully." 