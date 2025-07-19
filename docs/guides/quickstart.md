# Quick-Start: Run Your First iceOS Workflow

This guide shows how to install the SDK, estimate cost, and execute a *hello-world* chain that adds two numbers.

---

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install iceos  # once published; for local dev use `pip install -e .`
```

## 2. Inspect the Chain Spec

```json title="examples/mvp_demo/sum_chain.json"
{
  "version": "1.0.0",
  "name": "hello-sum",
  "nodes": [
    {
      "id": "sum1",
      "type": "skill",
      "name": "add_numbers",
      "tool_name": "sum",
      "tool_args": {"a": 2, "b": 3}
    }
  ]
}
```

* `type": "skill"` → invokes a deterministic action.
* `tool_name": "sum"` → maps to **SumSkill** shipped with the core.

## 3. Estimate Cost

```bash
ice run-chain examples/mvp_demo/sum_chain.json --estimate
```

Output (USD):
```json
{
  "estimated_cost_usd": 0.0
}
```
A pure Skill has no token cost.

## 4. Execute

```bash
ice run-chain examples/mvp_demo/sum_chain.json
```

Example result:
```json
{
  "success": true,
  "output": {
    "sum1": {
      "success": true,
      "output": {"result": 5}
    }
  }
}
```

---

That’s it! You just:
1. Parsed a JSON workflow via **MVPContract**.  
2. Validated + executed through **SkillGateway**.  
3. Got deterministic output without any external API calls.

Next steps:
* Explore `examples/` for more specs.
* Read `docs/architecture/` for layering rules.
* Create your own Skill by subclassing `ice_sdk.skills.base.SkillBase` and register it with `ServiceLocator["skill_gateway"].register(...)`. 