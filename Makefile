# Makefile for iceOS – minimal developer and CI tasks

.PHONY: lint-docker lock-check-docker type-check test ci fe-dev dev-db dev-migrate dev-api dev-up dev-down logs-api ci-guard-startup ci-dev-smoke docker-prune builder-prune prune-all

# Lint inside Docker (no local Python/Poetry needed)
lint-docker:
	docker run --rm -t \
		-v "$$PWD:/repo" -w /repo \
		python:3.11.9-slim bash -lc '\
		  python -m pip install --no-cache-dir --timeout 120 --retries 5 ruff==0.5.6 && \
		  ruff check . \
		'

# Verify Poetry lockfile is in sync using the builder stage (deterministic)
lock-check-docker:
	# Use the builder stage which already has Poetry installed to avoid flaky pip installs
	docker build --target builder -t iceos-builder . | cat
	docker run --rm -t \
		-v "$$PWD:/app" -w /app \
		iceos-builder poetry lock --check | cat

# Type-check via Docker image target (mypy --strict configured in image)
type-check:
	docker build --target devcheck -t iceos-devcheck . && \
		docker run --rm -t \
			-v "$$PWD/src:/app/src" \
			-v "$$PWD/typings:/app/typings" \
			-v "$$PWD/config:/app/config" \
			iceos-devcheck

# Unit tests (dockerized)
test:
	docker build --target test -t iceos-test . && \
		docker run --rm -t \
			-e ICE_ENABLE_INLINE_CODE=1 \
			-e ICE_COMPUTE_GRAPH_CENTRALITY=1 \
			-e ICE_STRICT_SERIALIZATION=1 \
			iceos-test pytest -c config/testing/pytest.ini -q -m unit

# CI aggregate
ci: lint-docker lock-check-docker type-check test ci-guard-startup ci-dev-smoke

# ---------------------------------------------------------------------------
# Frontend dev ---------------------------------------------------------------
# ---------------------------------------------------------------------------
fe-dev:
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Dev flow (Docker Compose) --------------------------------------------------
# ---------------------------------------------------------------------------
# Bring up Postgres and Redis only
dev-db:
	docker compose -f config/deploy/docker-compose.prod.yml --profile db up -d --remove-orphans postgres redis

# Run Alembic migrations once (one-off container)
dev-migrate:
	@echo "[migrate] Running Alembic upgrade head via one-off container..."; \
	docker compose -f config/deploy/docker-compose.prod.yml --profile db run --rm api alembic -c alembic.ini upgrade head | cat

# Start API and wait for readiness gate
dev-api:
	@echo "[api] Starting API..."; \
	docker compose -f config/deploy/docker-compose.prod.yml up -d --remove-orphans api; \
	printf "[api] Waiting for /readyz ..."; \
	READY=0; \
	for i in $$(seq 1 120); do \
	  if curl -fsS http://localhost:8000/readyz >/dev/null 2>&1; then READY=1; echo " ready"; break; fi; \
	  sleep 1; \
	done; \
	if [ $$READY -ne 1 ]; then \
	  echo "\n[api] Not ready after 120s. Last 200 lines:"; \
	  docker compose -f config/deploy/docker-compose.prod.yml logs --tail=200 api | cat; \
	  exit 1; \
	fi

# Full dev bring-up (DB/cache -> migrate -> API)
dev-up: dev-db dev-migrate dev-api

# Tear down all dev services
dev-down:
	docker compose -f config/deploy/docker-compose.prod.yml down -v --remove-orphans || true

# Tail API logs
logs-api:
	docker compose -f config/deploy/docker-compose.prod.yml logs -f api | cat

# ---------------------------------------------------------------------------
# CI helpers: startup guard and dev smoke -----------------------------------
# ---------------------------------------------------------------------------
ci-guard-startup:
	@echo "[ci-guard] Verifying no anyio.run in startup paths..."; \
	! grep -R "anyio\.run\(" src/ice_api/main.py src/ice_api/startup_utils.py src/ice_api/services/component_repo.py || (echo "Found forbidden anyio.run in startup code" >&2; exit 1)

ci-dev-smoke:
	@echo "[ci-smoke] Starting DB/cache..."; \
	docker compose -f config/deploy/docker-compose.prod.yml --profile db up -d --remove-orphans postgres redis; \
	echo "[ci-smoke] Running migrations..."; \
	docker compose -f config/deploy/docker-compose.prod.yml --profile db run --rm api alembic -c alembic.ini upgrade head | cat; \
	echo "[ci-smoke] Starting API..."; \
	docker compose -f config/deploy/docker-compose.prod.yml up -d --remove-orphans api; \
	printf "[ci-smoke] Waiting for /readyz ..."; \
	READY=0; for i in $$(seq 1 120); do \
	  if curl -fsS http://localhost:8000/readyz >/dev/null 2>&1; then READY=1; echo " ready"; break; fi; \
	  sleep 1; \
	done; \
	if [ $$READY -ne 1 ]; then \
	  echo "\n[ci-smoke] Not ready after 120s. Last 200 lines:"; \
	  docker compose -f config/deploy/docker-compose.prod.yml logs --tail=200 api | cat; \
	  exit 1; \
	fi

# ---------------------------------------------------------------------------
# Prune helpers --------------------------------------------------------------
# ---------------------------------------------------------------------------
docker-prune:
	docker image prune -f

builder-prune:
	docker builder prune -f

prune-all: docker-prune builder-prune
