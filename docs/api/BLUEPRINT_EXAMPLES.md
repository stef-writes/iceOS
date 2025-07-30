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

---

## Programmatic execution (production-style)

The runtime entry-point is always:

```python
from ice_orchestrator import initialize_orchestrator
from ice_orchestrator.services.workflow_execution_service import WorkflowExecutionService
from your_package.workflows import build_workflow  # returns a Workflow instance

initialize_orchestrator()            # registers context-manager & services

# Optionally register domain tools / agents **before** the workflow is built
from ice_core.unified_registry import registry as global_registry, NodeType
# global_registry.register_class(NodeType.TOOL, "my_tool", MyToolClass)

workflow = build_workflow()          # or WorkflowBuilder.build()
inputs   = {"your": "input"}       # will be available as {{inputs.your}}

result = await WorkflowExecutionService().execute_workflow(
    workflow.to_dict(),              # serialised spec
    inputs=inputs,                   # injected into GraphContext under "inputs"
)
print(result.success, result.output)
```

Key points:
1. **initialize_orchestrator()** must be called once at process start. It
   registers the global `GraphContextManager`, tool-service, LLM-service, etc.
2. Tools/agents must be registered _before_ the workflow is built so
   `populate_tool_node_schemas()` can discover them.
3. Pass end-user parameters through the `inputs` dict; the orchestrator stores
   them in the chain’s context as `{"inputs": …}` so every template like
   `{{inputs.foo}}` resolves automatically.

---

Response on validation error (HTTP 400):
```json
{
  "detail": [
    "Tool 'csv_reader' not found in registry",
    "Field 'model' is required for LLM node 'summ'"
  ]
}
``` 