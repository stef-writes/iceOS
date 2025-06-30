# Nodes, Tools & Agents

## Nodes
* **AiNodeConfig** – LLM-backed step with prompt, mappings and output schema.
* **ToolNodeConfig** – deterministic call to a registered tool.
* **ConditionNodeConfig** – branching logic based on context expression.

All nodes share common fields (id, dependencies, retries, timeout, etc.) defined in `BaseNodeConfig`.

## Tools
Implementation contract:
```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "Does something deterministic"
    parameters_schema = {...}

    async def run(self, **kwargs):
        ...
```

Tools must be side-effect free except inside `run` (repo rule #2) and declare a JSONSchema for parameters so LLMs can plan calls.

## Agents
An `AgentNode` embeds an LLM planner + limited tool set and can expose itself as a tool for recursive planning.  Cycle detection is enforced with a context-local stack to prevent infinite loops. 