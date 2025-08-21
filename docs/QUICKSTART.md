# iceOS Quickstart

## Prerequisites
- Docker + Docker Compose
- Set ICE_API_TOKEN (and provider keys if needed)

## Start services (compose)
```bash
make ci-integration
```

## Push and run a workflow (CLI)
```bash
export ICE_API_URL=http://localhost:8000
export ICE_API_TOKEN=dev-token
ice push examples/hello_world.json
ice run --last
```

## Upload and search documents (CLI)
```bash
ice uploads files --files README.md --scope kb
ice memory write --key doc1 --content "hello world" --scope kb
ice memory search --query "hello" --scope kb --top-k 3
```

## MCP tools via Postman
- Import config/postman/iceos.postman_collection.json
- Set baseUrl and apiToken
- Call MCP initialize then tools/call

## Health & registry
```bash
curl -s http://localhost:8000/readyz | jq
ice registry summary
```
