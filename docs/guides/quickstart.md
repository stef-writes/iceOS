# Quick-Start: Run Your First iceOS Workflow

This guide shows how to install the SDK, estimate cost, and execute a *hello-world* chain that adds two numbers.

---

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install iceos  # once published; for local dev use `pip install -e .`
```

## 2. Define a Blueprint

```json title="examples/mvp_demo/sum_blueprint.json"
{
  "version": "1.0.0",
  "name": "hello-sum",
  "nodes": [
    {
      "id": "sum1",
      "type": "tool",
      "tool_name": "sum",
      "tool_args": {"a": 2, "b": 3}
    }
  ]
}
```

* `type": "skill"` → invokes a deterministic action.
* `tool_name": "sum"` → maps to **SumSkill** shipped with the core.

## 3. Execute via MCP API

```bash
# 1) Register blueprint
curl -X POST http://localhost:8000/api/v1/mcp/blueprints \
     -H "Content-Type: application/json" \
     -d @examples/mvp_demo/sum_blueprint.json

# 2) Start run (returns run_id)
curl -X POST http://localhost:8000/api/v1/mcp/runs \
     -H "Content-Type: application/json" \
     -d '{"blueprint_id": "hello-sum"}'

# 3) Tail events (requires curl 7.72+)
curl --no-buffer http://localhost:8000/api/v1/mcp/runs/<run_id>/events

# 4) Get final result
curl http://localhost:8000/api/v1/mcp/runs/<run_id>
```

---

That’s it! You just:
1. Registered a **Blueprint** via MCP.  
2. Executed it through the orchestrator, with events streamed from Redis.  
3. Received deterministic output without external LLM cost.

Next steps:
* Explore `examples/` for more specs.
* Read `docs/architecture/` for layering rules.
* Create your own Skill by subclassing `ice_sdk.skills.base.SkillBase` and register it with `ServiceLocator["skill_gateway"].register(...)`. 