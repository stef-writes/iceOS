# Makefile for iceOS – minimal developer tasks

PYTHON := $(shell which python)

.PHONY: install lint lint-docker format format-check audit type type-nuke type-docker type-check test ci clean clean-caches precommit-clean fresh-env serve stop-serve dev pre-commit-docker pre-commit-docker-fix lock-check lock-check-docker run-min stop-min doctor-min

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
	# Use the builder stage which already has Poetry installed to avoid flaky pip installs
	docker build --target builder -t iceos-builder . | cat
	docker run --rm -t \
		-v "$$PWD:/app" -w /app \
		iceos-builder poetry lock --check | cat

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
	# Rebuild images with buildx + local cache to avoid stale code and speed up warm runs
	docker buildx create --use --name iceos-builder || true && \
	docker buildx build --load \
		--builder iceos-builder \
		--cache-to=type=local,dest=.cache/buildx,mode=max \
		--cache-from=type=local,src=.cache/buildx \
		--target api -t local/iceosv1a-api:dev . && \
	docker buildx build --load \
		--builder iceos-builder \
		--cache-to=type=local,dest=.cache/buildx,mode=max \
		--cache-from=type=local,src=.cache/buildx \
		--target test -t local/iceosv1a-itest:dev . && \
	IMAGE_REPO=local IMAGE_TAG=dev ICE_ENABLE_WASM=0 ICE_SKIP_STRESS=1 \
	docker compose -f docker-compose.itest.yml up --abort-on-container-exit --exit-code-from itest

# Run only wasm-marked tests with strict sandboxing (WASM enabled, seccomp not disabled)
ci-sandbox:
	IMAGE_REPO=local IMAGE_TAG=dev ICE_ENABLE_WASM=1 ICE_DISABLE_SECCOMP=0 \
	docker compose -f docker-compose.itest.yml run --rm itest bash -lc "pytest -c config/testing/pytest.ini -m wasm -q"

# Release gate: fast CI + strict sandbox subset must both pass
ci-release: ci ci-integration ci-sandbox

ci-live:
	# Run integration tests with real LLMs (no echo), external calls enabled.
	# Requires OPENAI_API_KEY/ANTHROPIC_API_KEY/... in the host env.
	IMAGE_REPO=local IMAGE_TAG=dev ICE_ENABLE_WASM=0 ICE_SKIP_STRESS=1 \
	OPENAI_API_KEY=$$OPENAI_API_KEY ANTHROPIC_API_KEY=$$ANTHROPIC_API_KEY GOOGLE_API_KEY=$$GOOGLE_API_KEY DEEPSEEK_API_KEY=$$DEEPSEEK_API_KEY \
	docker compose -f docker-compose.itest.yml -f docker-compose.livebuilder.yml up --abort-on-container-exit --exit-code-from itest

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
	PYTHONPATH=src:. uvicorn ice_api.main:app --port 8000 --reload

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
	USE_FAKE_REDIS=1 PYTHONPATH=src:. uvicorn ice_api.main:app --port 8000 --reload

# ---------------------------------------------------------------------------
# One-command RAG demo (compose up → ingest → query) -------------------------
# ---------------------------------------------------------------------------
.PHONY: demo-reset demo-up demo-wait demo-ingest demo-query demo-rag
## ----------------------------- Frontend -------------------------------------
.PHONY: fe-install fe-dev fe-build fe-start fe-up up down restart run demo-live

fe-install:
	cd frontend && npm install

fe-dev:
	cd frontend && npm run dev

fe-build:
	cd frontend && npm run build

fe-start:
	cd frontend && npm run start


# One-command up (API + DB + Redis + Frontend)
up:
	docker compose up -d --build --remove-orphans
	@echo "Waiting for API..."; \
	for i in $$(seq 1 120); do \
	  if curl -fsS http://localhost:8000/readyz >/dev/null 2>&1; then echo "API ready"; break; fi; \
	  sleep 1; \
	done
	@echo "Proxy → http://localhost (web) | API health: http://localhost/readyz"

down:
	docker compose down -v --remove-orphans

restart: down up

run:
	@echo "[run] Starting API + Web (Next rewrites /api → api:8000) ..."; \
	docker compose up -d --build --remove-orphans api web; \
	echo "[run] Waiting for Next dev to expose http://localhost:3000 ..."; \
	for i in $$(seq 1 120); do \
	  if curl -fsS http://localhost:3000 >/dev/null 2>&1; then echo "[ok] http://localhost:3000"; break; fi; \
	  sleep 1; \
	done; \
	if command -v open >/dev/null 2>&1; then open http://localhost:3000; fi

demo-live:
	@echo "[demo-live] Running one-time migrations..."; \
	 docker compose run --rm migrate >/dev/null 2>&1 || true; \
	 echo "[demo-live] Starting API + Web using existing images (no rebuild)..."; \
	 docker compose up -d --remove-orphans api web; \
	 echo "[demo-live] Waiting for API readiness at http://localhost:8000/readyz ..."; \
	 for i in $$(seq 1 120); do \
	   if curl -fsS http://localhost:8000/readyz >/dev/null 2>&1; then echo "[ok] API ready"; break; fi; \
	   sleep 1; \
	 done; \
	 echo "[demo-live] Waiting for Web at http://localhost:3000 ..."; \
	 for i in $$(seq 1 120); do \
	   if curl -fsS http://localhost:3000 >/dev/null 2>&1; then echo "[ok] Web ready: http://localhost:3000"; break; fi; \
	   sleep 1; \
	 done; \
	 if command -v open >/dev/null 2>&1; then open http://localhost:3000; fi; \
	 echo "[demo-live] TIP: API at http://localhost:8000 (token: dev-token). Frontend uses /api proxy path.";

.PHONY: demo-rebuild
demo-rebuild:
	@echo "[demo-rebuild] Rebuilding API and Web images..."; \
	 docker compose build api web; \
	 echo "[demo-rebuild] Done. Use 'make demo-live' to start without rebuilding."

.PHONY: run-native
run-native:
	bash scripts/dev/run_native.sh
## ---------------------------------------------------------------------------
## Minimal, zero-setup wrappers using a single env file ----------------------
## ---------------------------------------------------------------------------
.PHONY: run-min stop-min doctor-min

ENV_FILE ?= .env.dev

run-min:
	@echo "[run-min] Using env file: $(ENV_FILE)" ; \
	ENV_FILE=$(ENV_FILE) docker compose --env-file $(ENV_FILE) up -d postgres redis --remove-orphans ; \
	ENV_FILE=$(ENV_FILE) docker compose --env-file $(ENV_FILE) run --rm migrate ; \
	ENV_FILE=$(ENV_FILE) docker compose --env-file $(ENV_FILE) up -d api web --remove-orphans ; \
	printf "[run-min] Waiting for API /readyz ..." ; \
	for i in $$(seq 1 120); do \
	  curl -fsS http://localhost:8000/readyz >/dev/null 2>&1 && echo " ready" && break; \
	  sleep 1; \
	done ; \
	if command -v open >/dev/null 2>&1; then open http://localhost:3000; fi ; \
	echo "[ok] Web: http://localhost:3000  |  API: http://localhost:8000"

stop-min:
	ENV_FILE=$(ENV_FILE) docker compose --env-file $(ENV_FILE) down -v --remove-orphans || true

doctor-min:
	@echo "[doctor-min] API readiness:" ; (curl -fsS http://localhost:8000/readyz || true)
	@echo "[doctor-min] Ports: 8000($$(lsof -ti tcp:8000 | wc -l)) 3000($$(lsof -ti tcp:3000 | wc -l))"

# Single-origin zero-setup (compose: DB+cache+migrate+api+web+proxy)
.PHONY: run-auto
run-auto:
	$(MAKE) run

.PHONY: doctor
doctor:
	@echo "[doctor] Docker: $$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo unavailable)"; \
	echo "[doctor] Ports: 80($$(lsof -ti tcp:80 | wc -l)) 8000($$(lsof -ti tcp:8000 | wc -l)) 3000($$(lsof -ti tcp:3000 | wc -l))"; \
	echo "[doctor] API readiness:"; (curl -fsS http://localhost:8000/readyz || true); \
	echo "[doctor] Proxy readiness:"; (curl -fsS http://localhost/readyz || true)

.PHONY: reset
reset:
	docker compose down -v --remove-orphans || true

.PHONY: rebuild
rebuild:
	docker buildx create --use --name iceos-builder || true && \
	docker buildx build --load --builder iceos-builder --cache-to=type=local,dest=.cache/buildx,mode=max --cache-from=type=local,src=.cache/buildx --target api -t local/iceosv1a-api:dev . && \
	docker buildx build --load --builder iceos-builder --cache-to=type=local,dest=.cache/buildx,mode=max --cache-from=type=local,src=.cache/buildx --file frontend/Dockerfile --target runner -t local/iceosv1a-web:dev frontend

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
	@echo "[demo] Ingesting template seed assets into scope 'kb' via MCP tools/call...";
	docker compose exec api python - <<-'PY'
	import json, httpx
	BASE="http://localhost:8000"
	token="dev-token"
	files=[
	    "/app/plugins/bundles/library_assistant/examples/fake_bio.txt",
	    "/app/plugins/bundles/library_assistant/examples/fake_projects.txt",
	    "/app/plugins/bundles/library_assistant/examples/fake_resume.txt",
	    "/app/plugins/bundles/library_assistant/examples/fake_transcript.txt",
	]
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

# ---------------------------------------------------------------------------
# Supabase staging helpers ---------------------------------------------------
# ---------------------------------------------------------------------------
.PHONY: supabase-migrate supabase-rls-apply

# Run Alembic migrations against Supabase (requires DATABASE_URL env)
supabase-migrate:
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL is required (Supabase DSN)" >&2; exit 1; fi; \
	 echo "[supabase] Running migrations on $$DATABASE_URL"; \
	 docker compose run --rm -e DATABASE_URL migrate

# Apply RLS policies via psql in a disposable container
# Requires: PGHOST, PGPORT (optional), PGUSER, PGPASSWORD, PGDATABASE
supabase-rls-apply:
	@if [ -z "$$PGHOST" ] || [ -z "$$PGUSER" ] || [ -z "$$PGPASSWORD" ] || [ -z "$$PGDATABASE" ]; then \
	  echo "PGHOST, PGUSER, PGPASSWORD, PGDATABASE are required" >&2; exit 1; fi; \
	 docker run --rm -t \
	  -e PGPASSWORD \
	  -v "$$PWD/scripts/sql:/sql" \
	  postgres:15 bash -lc "psql -h $$PGHOST -U $$PGUSER -d $$PGDATABASE -f /sql/rls_policies.sql"

# ---------------------------------------------------------------------------
# Integration tests against Supabase staging --------------------------------
# ---------------------------------------------------------------------------
.PHONY: ci-integration-staging
ci-integration-staging:
	@if [ -z "$$DATABASE_URL" ]; then echo "DATABASE_URL is required, e.g. export DATABASE_URL=postgresql+asyncpg://user:pass@aws-0-us-east-2.pooler.supabase.com:6543/postgres" >&2; exit 1; fi; \
	 echo "[itest-staging] Using DATABASE_URL=$$DATABASE_URL"; \
	docker buildx create --use --name iceos-builder || true && \
	docker buildx build --load --builder iceos-builder --cache-to=type=local,dest=.cache/buildx,mode=max --cache-from=type=local,src=.cache/buildx --target api -t local/iceosv1a-api:dev . && \
	docker buildx build --load --builder iceos-builder --cache-to=type=local,dest=.cache/buildx,mode=max --cache-from=type=local,src=.cache/buildx --target test -t local/iceosv1a-itest:dev . && \
	IMAGE_REPO=local IMAGE_TAG=dev ICE_ENABLE_WASM=0 ICE_SKIP_STRESS=1 \
	DATABASE_URL=$$DATABASE_URL \
	docker compose -f docker-compose.itest.yml -f docker-compose.itest.staging.yml up --abort-on-container-exit --exit-code-from itest

.PHONY: stage-up
stage-up:
	@if [ ! -f ./.env.supabase.final ]; then echo "Missing .env.supabase.final with Supabase DSNs" >&2; exit 1; fi; \
	 set -a; . ./.env.supabase.final; set +a; \
	 echo "[stage] Running Alembic migrations on Supabase..."; \
	 docker compose -f docker-compose.yml run --rm --no-deps -e DATABASE_URL -e ALEMBIC_SYNC_URL migrate; \
	 echo "[stage] Starting API with staging override..."; \
	 docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --remove-orphans api; \
	 echo "[stage] Waiting for API readiness at http://localhost:8000/readyz ..."; \
	 for i in $$(seq 1 90); do \
	   if curl -fsS http://localhost:8000/readyz >/dev/null 2>&1; then echo "[stage] API ready"; exit 0; fi; \
	   sleep 1; \
	 done; \
	 echo "[stage] API did not become ready in time" >&2; exit 1
