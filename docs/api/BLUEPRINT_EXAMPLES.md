# Example: Validate a Blueprint without registering it

```bash
curl -X POST http://localhost:8000/api/v1/mcp/blueprints \
     -H "Content-Type: application/json" \
     -d '{
           "validate_only": true,
           "nodes": [
             {"id": "parse", "type": "tool", "tool_name": "csv_reader"},
             {"id": "summ", "type": "llm", "prompt": "Summarise", "model": "gpt-4o"}
           ]
         }'
```

Response on success:
```json
{
  "blueprint_id": "bp_a1b2c3d4",
  "status": "accepted"
}
```

Response on validation error (HTTP 400):
```json
{
  "detail": [
    "Tool 'csv_reader' not found in registry",
    "Field 'model' is required for LLM node 'summ'"
  ]
}
``` 