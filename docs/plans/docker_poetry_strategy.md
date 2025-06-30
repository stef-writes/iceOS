d# iceOS Deployment & Packaging Strategy

_Revision: 2025-XX-XX_

This document explains **how we use Poetry and Docker today**, the **options we have for packaging & deploying** the platform tomorrow, and **step-by-step check-lists** so we can move smoothly from local hacking to a fully containerised, micro-service architecture.

---
## 1 Current state

| Layer | Tooling | Purpose | Where we use it |
|-------|---------|---------|-----------------|
| Python dependency + virtual-env | **Poetry** (`pyproject.toml` + `poetry.lock`) | • Pin exact versions<br>• Create per-project virtual-env | Local dev, CI
| System-level isolation | **Docker** (pulled via `testcontainers`) | Spin up throw-away services for tests (httpbin, Postgres, …) | CI + contract/integration tests only

There is **no application Docker image yet**; the platform is started locally with:
```bash
poetry install
poetry run uvicorn app.main:app --reload
```

---
## 2 Why we keep both tools

• **Poetry = repeatable Python layer**  
  – Guarantees every dev/CI host has the same package set.  
  – Handles publishing to PyPI for power users who want `pip install iceos`.

• **Docker = repeatable OS/process layer**  
  – Freezes OS libs (libssl, libc, …) & shell tools.  
  – Lets us scale / isolate services in production or spin up side-car services in tests.

Using both means we can:
1. Develop quickly (no Docker build loop).
2. Ship a one-liner to self-hosters (`docker run …`).
3. Later break the monolith into multiple containers without changing dev workflow.

---
## 3 Roadmap of packaging modes

| Milestone | Target audience | Packaging | Status |
|-----------|-----------------|-----------|--------|
| **M0** – Local dev & CI | Core team | Poetry virtual-env | ✅ (today)
| **M1** – Single-container release | Self-hosters, staging | One Docker image with Poetry inside | 🔜
| **M2** – Multi-container deployment | SaaS / prod scale | Compose / Kubernetes (UI, Orchestrator, Nodes) | Future
| **M3** – Language-agnostic Nodes | Plugin authors | Per-node images (Python, JS, JVM, etc.) | Future

---
## 4 M1  •  One-image recipe

Create `Dockerfile` at repo root:
```dockerfile
FROM python:3.11-slim

# ‑- Poetry -----------------------------------------------------------------
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install "poetry==$POETRY_VERSION"
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# ‑- Install deps first (cached layer) --------------------------------------
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-root --only main

# ‑- Copy source -------------------------------------------------------------
COPY src /app/src

# ‑- Entrypoint --------------------------------------------------------------
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build & test locally:
```bash
docker build -t iceos:latest .
docker run -p 8000:8000 iceos:latest
```

CI addition (`.github/workflows/ci.yml` snippet):
```yaml
      - name: Build app image
        run: docker build -t ghcr.io/iceos/iceos:${{ github.sha }} .
```

Publish with GitHub Actions or push manually.

---
## 5 M2  •  Breaking into services

When traffic or team velocity warrants, split into independent images:

| Service | Image name | Port | Notes |
|---------|-----------|------|-------|
| Public REST / UI | `iceos/web` | 80 | Next-JS or FastAPI "canvas" front-end |
| Orchestrator API | `iceos/orchestrator` | 9000 | Schedules chains, manages events |
| Built-in Nodes   | `iceos/nodes-std` | — | Package of light Python tools |
| Heavy Nodes (GPU/Large models) | `iceos/node-llm` | — | Can scale separately |
| Postgres / Redis | upstream images | — | state & queues |

Example `docker-compose.yml` skeleton:
```yaml
version: "3.9"
services:
  web:
    image: iceos/web:${TAG}
    depends_on: [orchestrator]
    ports: ["80:80"]
  orchestrator:
    image: iceos/orchestrator:${TAG}
    environment:
      DB_URL: postgres://...
    depends_on: [db]
  db:
    image: postgres:16
    volumes: [db-data:/var/lib/postgresql/data]
volumes:
  db-data:
```

Later swap Compose for Helm charts if you move to Kubernetes.

---
## 6 Guidelines for Node authors

1. **Side-effect isolation** – All external effects live _only_ inside `Tool.run()` implementations (repo rule #2).  This makes it trivial to ship each Tool as its own container/API.
2. **Async I/O** – Keep `run()` async to avoid blocking orchestrator threads when nodes are co-located.
3. **Environment contracts** – Node images expose:
   * Health endpoint at `/healthz` (HTTP 200 = OK)
   * Metadata at `/openapi.json` so orchestrator can discover inputs/outputs.
4. **Versioning** – Bump image tags with semantic versioning; orchestrator chooses compat image based on chain requirements.

---
## 7 When to move to the next milestone

| Symptom | Consider… |
|---------|-----------|
| You want one-liner install for beta testers | M1 (single image) |
| CPU spikes in Orchestrator starve UI | M2 (split UI / orchestrator) |
| Large-model node needs GPU | M2/M3 (dedicated node image on GPU pool) |
| External contributors publish their own nodes | M3 (per-node images, registry) |

---
## 8 Reference commands cheat-sheet

```bash
# Local dev
poetry install              # once
poetry run uvicorn app.main:app --reload

# Run full tests (uses Docker for contract tests)
make test                   # or poetry run pytest -m "not slow"

# Build single-image release
TAG=$(git rev-parse --short HEAD)
docker build -t iceos:${TAG} .

docker run -p 8000:8000 iceos:${TAG}

# Compose stack (once images exist)
docker compose up -d
```

---
## 9 Appendix – glossary

| Term | Meaning |
|------|---------|
| **Poetry** | Python dependency & packaging tool; replaces `pip + virtualenv + setup.py` |
| **Docker image** | Read-only template (like a OS snapshot) used to start containers |
| **Container** | Running instance of an image, isolated by the host kernel |
| **Monolith** | One process/image containing whole app |
| **Micro-service** | Many small images/processes communicating over APIs |
| **Testcontainers** | Library that spins up Docker containers during tests |

---
### End of document 