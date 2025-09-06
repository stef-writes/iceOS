n whyu## Your Asset Library

This page explains where your assets live, how to register/list/update them, and how runtime rehydration makes them available for execution.

### Asset types
- Components: tools, agents, workflows, and code factories. Persisted in the component repository (Postgres). Rehydrated into the unified registry at API startup.
- Blueprints: design-time workflow DAGs. Persisted in Postgres; Redis used as cache.
- User assets: free-form content in semantic memory (scope "library").

### Registering components
1) Validate/optionally auto_register via API:
```bash
curl -sS -X POST http://localhost:8000/api/v1/mcp/components/validate \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' \
  -d '{"type":"tool","name":"csv_loader","tool_class_code":"..."}'
```
2) Persist to repository (recommended):
```bash
curl -sS -X POST http://localhost:8000/api/v1/mcp/components/register \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' \
  -d '{"type":"tool","name":"csv_loader","tool_class_code":"..."}'
```

List components:
```bash
curl -sS http://localhost:8000/api/v1/mcp/components -H 'Authorization: Bearer dev-token'
```

Update component (optimistic concurrency):
```bash
LOCK=$(curl -sS -D - http://localhost:8000/api/v1/mcp/components/tool/csv_loader \
  -H 'Authorization: Bearer dev-token' | awk '/X-Version-Lock/ {print $2}')
curl -sS -X PUT http://localhost:8000/api/v1/mcp/components/tool/csv_loader \
  -H 'Authorization: Bearer dev-token' -H "X-Version-Lock: ${LOCK}" \
  -H 'Content-Type: application/json' -d @updated_definition.json
```

### Blueprints
- Create (optimistic lock):
```bash
curl -sS -X POST http://localhost:8000/api/v1/blueprints/ \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' -H 'X-Version-Lock: __new__' \
  -d '{"schema_version":"1.2.0","nodes":[{"id":"llm1","type":"llm","provider":"openai","model":"gpt-4o","prompt":"Say hi"}]}'
```
- Run by id:
```bash
curl -sS -X POST 'http://localhost:8000/api/v1/executions/?wait_seconds=5' \
  -H 'Authorization: Bearer dev-token' -H 'Content-Type: application/json' \
  -d '{"blueprint_id":"<id>","inputs":{}}'
```

### Unified Library listing
List/search components and blueprints together:
```bash
curl -sS 'http://localhost:8000/api/v1/library/assets/index?q=rag&kind=component' \
  -H 'Authorization: Bearer dev-token'
```
Filters (UI): `kind` (component|blueprint), `type` (tool|agent|workflow|code), `q` (substring), `sort` (updated|name).

### Client helpers
```python
from ice_client import IceClient

client = IceClient('http://localhost:8000')
# List all assets (first 50)
print(await client.list_library())
# Run bundle by id with fallback YAML registration
exec_id = await client.run_bundle('chatkit.rag_chat', inputs={"query":"Hi"}, blueprint_yaml_path='Plugins/bundles/chatkit/workflows/rag_chat.yaml', wait_seconds=5)
```

### Startup rehydration
On API start, repository definitions are re-registered into the unified registry so your tools/agents/workflows are executable without manual imports. Blueprints are loaded on-demand (DB-first; Redis cache as a fast path).
