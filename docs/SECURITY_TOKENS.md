# Security & Tokens

Issue, list, revoke tokens via the API. Tokens carry optional org/project/user and scopes.

## Issue a token
```bash
curl -sS -X POST \
  -H "Authorization: Bearer $ICE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"org_id":"demo_org","user_id":"demo_user","scopes":["memory:write","memory:search"],"ttl_days":30}' \
  "$ICE_API_URL/api/v1/tokens/"
```

Response contains the raw `token` (shown once) and `token_hash` persisted server-side.

## List tokens
```bash
curl -sS -H "Authorization: Bearer $ICE_API_TOKEN" "$ICE_API_URL/api/v1/tokens/"
```

## Revoke a token
```bash
curl -sS -X POST -H "Authorization: Bearer $ICE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token_hash":"<hash>"}' \
  "$ICE_API_URL/api/v1/tokens/revoke"
```

Scopes are enforced via policy helpers; wire required scopes per route/tool as needed.
