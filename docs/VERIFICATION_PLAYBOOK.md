# Verification Playbook (Frontend → API → LLM)

This is the exact, repeatable set of steps to prove live functionality via the frontend. Use it daily before demos and before publishing.

## Prereqs
- Docker + Docker Compose
- OPENAI_API_KEY (and optional providers) exported in your shell

## One-time DB migration
```bash
docker compose run --rm migrate
```

## Start stack (frontend + api)
```bash
make demo-live
```

## Health
```bash
# Frontend origin
curl -fsS http://localhost:3000/readyz
# API direct
curl -fsS http://localhost:8000/readyz
```

## Templates → Blueprint (via frontend)
```bash
TOKEN=dev-token
# List
curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://localhost:3000/api/v1/templates/
# Materialize ChatKit RAG workflow
BP_ID=$(curl -fsS -X POST http://localhost:3000/api/v1/templates/from-workflow \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"workflow_id":"chatkit.rag_chat"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
```

## Execute (wait for final result)
```bash
curl -fsS -X POST "http://localhost:3000/api/v1/executions/?wait_seconds=20" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"payload\":{\"blueprint_id\":\"$BP_ID\",\"inputs\":{\"query\":\"Say hello in 10 words.\",\"org_id\":\"demo_org\",\"user_id\":\"demo_user\",\"session_id\":\"frontend_proof\"}}}"
```
Expected: JSON with "status":"completed" and non-empty "result".

## Library (optional RAG content)
```bash
# Add a document to semantic memory
curl -fsS -X POST http://localhost:8000/api/v1/library/assets \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"label":"bio","content":"Stefano is a product-focused engineer.","mime":"text/plain","org_id":"demo_org","user_id":"demo_user"}'
# List
curl -fsS 'http://localhost:8000/api/v1/library/assets?user_id=demo_user&limit=5' \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting
- 422 Unprocessable Entity: Ensure Authorization header and exact body shape (executions require {"payload":{...}}), include Content-Type json.
- 500 on library/templates: run migrations (see above) and retry.
- Use API direct (8000) for cURL to avoid following rewrites to internal hosts.
