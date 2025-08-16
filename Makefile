# Makefile for iceOS – minimal developer tasks

PYTHON := $(shell which python)

.PHONY: install lint lint-docker format format-check audit type type-nuke type-docker type-check test ci clean clean-caches precommit-clean fresh-env serve stop-serve dev pre-commit-docker pre-commit-docker-fix

install:
	poetry install --with dev --no-interaction

lint:
	poetry run ruff check src tests
	poetry run isort --check-only src tests

# Lint inside Docker (no local Python/Poetry needed)
lint-docker:
	docker run --rm -t \
		-v "$$PWD:/repo" -w /repo \
		python:3.11.9-slim bash -lc '\
		  python -m pip install --no-cache-dir --timeout 120 --retries 5 ruff==0.5.6 && \
		  ruff check . \
		'

format:
	poetry run isort src tests
	poetry run black src tests

format-check:
	poetry run isort --check-only src tests
	poetry run black --check src tests

type:
	poetry run mypy --config-file config/typing/mypy.ini src

type-check:
	docker build --target devcheck -t iceos-devcheck . && \
	docker run --rm -t \
		-v "$$PWD/src:/app/src" \
		-v "$$PWD/typings:/app/typings" \
		-v "$$PWD/config:/app/config" \
		iceos-devcheck

type-nuke:
	MYPY_CACHE_DIR=/dev/null poetry run mypy --no-incremental --config-file config/typing/mypy.ini src

type-docker:
	docker build --target devcheck -t iceos-devcheck . | cat
	docker run --rm -t \
	  -v "$(PWD)/src:/app/src" \
	  -v "$(PWD)/typings:/app/typings" \
	  -v "$(PWD)/config:/app/config" \
	  iceos-devcheck | cat

test:
	docker build --target test -t iceos-test . && \
	docker run --rm -t \
		-e ICE_ENABLE_INLINE_CODE=1 \
		-e ICE_COMPUTE_GRAPH_CENTRALITY=1 \
		-e ICE_STRICT_SERIALIZATION=1 \
		iceos-test pytest -c config/testing/pytest.ini tests/unit -q --ignore=tests/unit/ice_builder --ignore=tests/unit/ice_cli

ci: lint-docker type-check test

ci-integration:
	IMAGE_REPO=local IMAGE_TAG=dev ICE_ENABLE_WASM=0 ICE_SKIP_STRESS=1 \
	docker compose -f docker-compose.itest.yml up --abort-on-container-exit --exit-code-from itest

ci-wasm:
	IMAGE_REPO=local IMAGE_TAG=dev ICE_ENABLE_WASM=1 ICE_SKIP_STRESS=1 \
	docker compose -f docker-compose.itest.yml run --rm itest bash -lc "pytest -c config/testing/pytest.ini -m wasm -q"

# ---------------------------------------------------------------------------
# Dockerized pre-commit (no local Python/Poetry required) --------------------
# ---------------------------------------------------------------------------
pre-commit-docker:
	docker run --rm -t \
		-v "$$PWD:/repo" -w /repo \
		python:3.11.9-slim bash -lc '\
		  apt-get update -qq && apt-get install -y -qq git && rm -rf /var/lib/apt/lists/* && \
		  python -m pip install --no-cache-dir --timeout 120 --retries 5 pre-commit==3.7.1 && \
		  pre-commit run --all-files --show-diff-on-failure \
		'

pre-commit-docker-fix:
	$(MAKE) pre-commit-docker || $(MAKE) pre-commit-docker

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

clean-caches: clean

precommit-clean:
	pre-commit clean || true

fresh-env: clean-caches precommit-clean
	rm -rf .venv
	poetry cache clear --all pypi -n || true
	poetry install --with dev --no-interaction --sync

# Zero-setup dev server (no Docker, in-memory Redis stub)
.PHONY: dev-zero
dev-zero:
	USE_FAKE_REDIS=1 PYTHONPATH=src uvicorn ice_api.main:app --port 8000 --reload
