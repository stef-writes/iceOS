# Makefile for iceOS – minimal developer tasks

PYTHON := $(shell which python)

.PHONY: install lint lint-docker format format-check audit type type-nuke type-docker type-check test ci clean clean-caches precommit-clean fresh-env serve stop-serve dev pre-commit-docker pre-commit-docker-fix lock-check lock-check-docker

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

lock-check:
	poetry lock --check || (echo "Lock drift detected. Run 'poetry lock --no-update' locally and commit the lockfile." && exit 1)

lock-check-docker:
	docker run --rm -t \
		-v "$$PWD:/repo" -w /repo \
		python:3.11.9-slim bash -lc '\
		  python -m pip install --no-cache-dir --timeout 120 --retries 5 poetry==1.8.3 && \
		  poetry lock --check \
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

# Coverage (unit tests)
COV_MIN ?= 85

test:
	docker build --target test -t iceos-test . && \
		docker run --rm -t \
			-e ICE_ENABLE_INLINE_CODE=1 \
			-e ICE_COMPUTE_GRAPH_CENTRALITY=1 \
			-e ICE_STRICT_SERIALIZATION=1 \
			iceos-test pytest -c config/testing/pytest.ini -q -m unit

# Coverage gate target (unit tests with coverage)
test-coverage:
	docker build --target test -t iceos-test . && \
		docker run --rm -t \
			-e ICE_ENABLE_INLINE_CODE=1 \
			-e ICE_COMPUTE_GRAPH_CENTRALITY=1 \
			-e ICE_STRICT_SERIALIZATION=1 \
			iceos-test pytest -c config/testing/pytest.ini --cov=src --cov-report=term-missing --cov-fail-under=$(COV_MIN) -q -m unit

ci: lint-docker lock-check-docker type-check test

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
	OPENAI_API_KEY=$$OPENAI_API_KEY SERPAPI_KEY=$$SERPAPI_KEY poetry run python scripts/ops/verify_runtime.py

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

# ---------------------------------------------------------------------------
# One-command RAG demo (compose up → ingest → query) -------------------------
# ---------------------------------------------------------------------------
.PHONY: demo-reset demo-up demo-wait demo-ingest demo-query demo-rag

# Default demo query (override with: make demo-query Q="...your question...")
Q ?= Give me a two-sentence professional summary for Stefano.
WARMUPS ?= 1
RUNS ?= 3

demo-reset:
	docker compose down -v || true

demo-up:
	# Start DB and Redis first
	docker compose up -d postgres redis --remove-orphans
	# Run one-shot migrations to head
	docker compose run --rm migrate
	# Start API after successful migrations
	docker compose up -d api

demo-wait:
	@echo "[demo] Waiting for API readiness at http://localhost:8000/readyz ..."; \
	for i in $$(seq 1 120); do \
	  if curl -fsS http://localhost:8000/readyz >/dev/null 2>&1; then \
	    echo "[demo] API ready"; exit 0; \
	  fi; \
	  sleep 1; \
	done; \
	echo "[demo] API did not become ready in time" >&2; exit 1

demo-ingest:
	@echo "[demo] Ingesting example assets into scope 'kb' via MCP tools/call...";
	docker compose exec api python - <<-'PY'
	import json, httpx
	BASE="http://localhost:8000"
	token="dev-token"
	files=["/app/examples/user_assets/resume.txt","/app/examples/user_assets/cover_letter.txt","/app/examples/user_assets/website.txt"]
	with httpx.Client() as c:
	    c.post(f"{BASE}/api/v1/mcp/", json={"jsonrpc":"2.0","id":0,"method":"initialize","params":{}} , headers={"Authorization": f"Bearer {token}"}).raise_for_status()
	    for fp in files:
	        text=open(fp, "r", encoding="utf-8").read()
	        payload={"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"tool:memory_write_tool","arguments":{"inputs":{"key":fp.split('/')[-1],"content":text,"scope":"kb"}}}}
	        c.post(f"{BASE}/api/v1/mcp/", json=payload, headers={"Authorization": f"Bearer {token}"}).raise_for_status()
	print("[demo] Ingestion complete")
	PY

demo-query:
	@echo "[demo] Running demo query via ChatKit Bundle: $(Q)";
	docker compose exec api python - <<-'PY'
	import json, httpx
	BASE="http://localhost:8000"; token="dev-token"
	payload={"blueprint_id":"chatkit.rag_chat","inputs":{"query":"$(Q)","org_id":"demo_org","user_id":"demo_user","session_id":"chat_demo"}}
	with httpx.Client() as c:
	    r=c.post(f"{BASE}/api/v1/executions/", json=payload, headers={"Authorization": f"Bearer {token}"}); r.raise_for_status(); exec_id=r.json()["execution_id"]
	    for _ in range(120):
	        st=c.get(f"{BASE}/api/v1/executions/{exec_id}", headers={"Authorization": f"Bearer {token}"});
	        if st.json().get("status") in {"completed","failed"}: print(json.dumps(st.json(), indent=2)); break
	PY

demo-rag: demo-up demo-wait demo-ingest demo-query

# ---------------------------------------------------------------------------
# Benchmarks ---------------------------------------------------------------
# ---------------------------------------------------------------------------
.PHONY: bench-chatkit
bench-chatkit:
	@echo "[bench] Running ChatKit bundle benchmarks..."; \
	ICE_API_URL=$${ICE_API_URL:-http://localhost:8000} \
	ICE_API_TOKEN=$${ICE_API_TOKEN:-dev-token} \
	BENCH_QUERY="$(Q)" \
	BENCH_WARMUPS=$(WARMUPS) BENCH_RUNS=$(RUNS) \
	python scripts/ops/run_chatkit_bench.py
