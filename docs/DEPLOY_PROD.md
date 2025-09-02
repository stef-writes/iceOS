Production deployment (compose + secrets)

Secrets policy
- Never bake provider keys into images or commit them to the repo.
- Inject at deploy-time from your secret manager (host/VM env, 1Password CLI, AWS SSM/Secrets Manager, GCP Secret Manager, Vault).
- Rotate centrally; containers read via env vars only.

Compose (prod)
Use the prod override `config/deploy/docker-compose.prod.yml` and pass secrets via environment at runtime:

Example (host/VM):
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="..."
export GOOGLE_API_KEY="..."
export DEEPSEEK_API_KEY="..."
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/iceos"
export ALEMBIC_SYNC_URL="postgresql://user:pass@host:5432/iceos"
export ORG_BUDGET_USD=5.00

docker compose -f docker-compose.yml \
  -f config/deploy/docker-compose.prod.yml up -d api

curl -fsS http://localhost:8000/readyz
```

Notes
- Prefer managed Postgres/pgvector for production; disable the included `postgres` service and point `DATABASE_URL` to the managed DSN.
- For Kubernetes, mirror these env vars using Secrets (or External Secrets). Mount as env in the `api` pod.
- Budget/governance can be tuned via env `ORG_BUDGET_USD` and server-side allowlists.

CI/CD (GitHub Actions example)
- Store secrets in GitHub → Settings → Secrets and variables → Actions.
- At deploy, inject them as env when starting services on the target (runner or remote host).

Minimal job snippet:
```yaml
name: Deploy
on: [workflow_dispatch]
jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
      DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      ALEMBIC_SYNC_URL: ${{ secrets.ALEMBIC_SYNC_URL }}
      ORG_BUDGET_USD: "5.00"
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Build images
        run: docker compose build --pull --no-cache
      - name: Start API
        run: |
          docker compose -f docker-compose.yml \
            -f config/deploy/docker-compose.prod.yml up -d api
      - name: Health
        run: |
          for i in {1..60}; do curl -fsS http://localhost:8000/readyz && exit 0; sleep 1; done; exit 1
```

Operational tips
- Enable WASM (`ICE_ENABLE_WASM=1`) to keep code nodes sandboxed in prod.
- Keep `ICE_BUILDER_USE_PROMPT_PLANNER=1` and `ICE_SKIP_EXTERNAL=0` for live builder use.
- Log budgets and model selections for auditability.
