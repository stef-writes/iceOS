# iceOS Node Engineering Workshops

These hands-on labs guide you through building robust nodes and workflows. Each lab includes goals, steps, commands, and acceptance criteria.

## Lab 1 – Author a Tool and run it in a Blueprint

- Goal: Create a new Tool, validate, push a blueprint, and run it.
- Steps
  1) Scaffold:
     - `ice new tool pricing_tool --description "Compute price with margin"`
  2) Implement `_execute_impl(self, *, cost: float) -> Dict[str, Any]` to return `{ "price": round(cost * (1 + self.margin_percent/100.0), 2) }`.
  3) Author `examples/pricing.yaml`:
     ```yaml
     schema_version: "1.2.0"
     metadata: { draft_name: pricing_flow }
     nodes:
       - id: n1
         type: tool
         name: pricing
         tool_name: pricing_tool
         dependencies: []
     ```
  4) Build + push + run:
     - `ice build examples/pricing.yaml --output examples/pricing.json`
     - `ICE_API_TOKEN=dev-token ice push examples/pricing.json --api http://localhost:8000 --token $ICE_API_TOKEN`
     - `ice run <blueprint_id> --api http://localhost:8000 --token $ICE_API_TOKEN --input cost=100`
- Acceptance
  - Execution completes with `status: completed` and output contains `price`.
  - `GET /api/v1/meta/nodes` lists the tool with schemas.

## Lab 2 – Agent with memory, planning, and multi-tool selection

- Goal: Build an `agent` node that uses multiple tools, maintains state, and advances toward a goal.
- Steps
  1) Create/reuse two tools (e.g., `lookup_tool`, `writer_tool`).
  2) Author `examples/research_writer.yaml`:
     ```yaml
     schema_version: "1.2.0"
     metadata: { draft_name: research_writer }
     nodes:
       - id: t1
         type: tool
         name: lookup
         tool_name: lookup_tool
         dependencies: []
       - id: t2
         type: tool
         name: writer
         tool_name: writer_tool
         dependencies: [t1]
       - id: a1
         type: agent
         name: research_agent
         package: my_pkg.agent_impl
         tools: []
         memory: { kind: "working" }
         max_iterations: 5
         dependencies: [t1]
     ```
  3) Implement the agent class (module exposed by `package`) matching `ice_core.protocols.agent.IAgent` and register via the agent registry.
  4) Validate: `GET /api/v1/meta/nodes/agent/schema` and `POST /api/v1/mcp/components/validate`.
  5) Build + push + run; observe decisions.
- Acceptance
  - Agent runs ≤ `max_iterations`, uses at least one tool, and returns a final output.
  - Memory affects subsequent steps (e.g., working context).

## Lab 3 – Goal system with monitoring and conditional control

- Goal: Combine `monitor` + `condition` to enforce simple SLOs and branch.
- Steps
  1) Author `examples/goal_system.yaml`:
     ```yaml
     schema_version: "1.2.0"
     metadata: { draft_name: goal_system }
     nodes:
       - id: n1
         type: tool
         name: compute
         tool_name: pricing_tool
       - id: m1
         type: monitor
         name: quality_gate
         dependencies: [n1]
       - id: c1
         type: condition
         expression: "${quality_gate.triggered} == false"
         dependencies: [m1]
     ```
  2) Ensure `monitor` returns `triggered` in its output.
  3) Optionally set a `RetryPolicy` on `n1` (see node catalog schema hints).
  4) Build + push + run.
- Acceptance
  - When gate passes, condition follows true path; otherwise follows false path.

## Lab 4 – Budget governance

- Goal: Demonstrate deterministic cost preflight.
- Steps
  1) `export ORG_BUDGET_USD=0.01`.
  2) `POST /api/v1/executions` with a blueprint expected to exceed budget.
- Acceptance
  - API returns `402 Payment Required` with structured details; run is not started.

## Lab 5 – Observability: live streaming

- Goal: Observe execution events in real-time.
- Steps
  1) Start an execution; in parallel, connect:
     - WS: `ws://localhost:8000/ws/executions/{execution_id}`
     - or use `ice run` (polling) to stream status.
- Acceptance
  - Receive node/workflow start and completion events; terminal shows final result.

---

Tips
- Prefer JSON/YAML blueprints for API submission; use `ice build` for Python DSL.
- Use catalog endpoints to render configuration forms with `ui_hints`.
- Authenticate with `ICE_API_TOKEN` for both REST and WS`

---

## Appendix – Working agent example (planning + tools + memory)

### Agent implementation (place in `src/ice_tools/generated/research_agent.py`)

```python
"""ResearchAgent – minimal planning agent using two tools.

Implements a structured decide() loop that selects tools and updates memory.

Example
-------
>>> # Factory import path: "ice_tools.generated.research_agent:create_research_agent"
>>> # Registered name: "research_agent"
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel

from ice_core.unified_registry import register_agent_factory


class ResearchAgent(BaseModel):
    """Simple agent that looks up data then writes a summary.

    Parameters
    ----------
    goal : str
        High-level intent for the agent.

    Example
    -------
    >>> agent = create_research_agent(goal="summarize topic")
    >>> # AgentRuntime will call decide()/allowed_tools()/observe()
    """

    goal: str = "summarize"

    def allowed_tools(self) -> List[str]:  # noqa: D401
        """List of tools agent is allowed to call."""
        return [
            "lookup_tool",  # expected to exist
            "writer_tool",  # expected to exist
        ]

    async def think(self, context: Dict[str, Any]) -> str:  # noqa: D401
        """Fallback single-step reasoning when decide() is not used."""
        topic = context.get("topic", "")
        return f"I would research '{topic}' and write a summary."

    def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        """Structured decision step for plan→act→observe loop.

        Returns a dict with keys: tool|inputs|done|message.
        """
        memory = context.setdefault("agent", {})
        last_tool = memory.get("last_tool")
        topic = context.get("topic", "")

        if not last_tool:
            return {
                "message": f"Looking up information about '{topic}'",
                "tool": "lookup_tool",
                "inputs": {"query": topic},
                "done": False,
            }

        # If we already looked up, proceed to writing
        if last_tool == "lookup_tool" and "last_result" in memory:
            notes = memory["last_result"].get("notes", "")
            return {
                "message": "Drafting summary from notes",
                "tool": "writer_tool",
                "inputs": {"notes": notes, "style": "concise"},
                "done": True,  # finish after writing
            }

        return {"message": "No further action", "done": True}

    def observe(self, context: Dict[str, Any], result: Dict[str, Any]) -> None:  # noqa: D401
        """Update working memory after each tool call."""
        memory = context.setdefault("agent", {})
        memory.setdefault("history", []).append(result)


def create_research_agent(**kwargs: Any) -> ResearchAgent:
    """Factory: create a `ResearchAgent` with validated kwargs.

    Parameters
    ----------
    **kwargs : Any
        Keyword arguments forwarded to the agent model.

    Returns
    -------
    ResearchAgent
        Instance ready to be executed by `AgentRuntime`.
    """

    return ResearchAgent(**kwargs)


# Auto-registration (name → import path)
register_agent_factory(
    "research_agent",
    "ice_tools.generated.research_agent:create_research_agent",
)
```

### Blueprint wiring the agent and tools (`examples/research_writer.yaml`)

```yaml
schema_version: "1.2.0"
metadata:
  draft_name: research_writer
nodes:
  - id: t1
    type: tool
    name: lookup
    tool_name: lookup_tool
    dependencies: []
  - id: t2
    type: tool
    name: writer
    tool_name: writer_tool
    dependencies: [t1]
  - id: a1
    type: agent
    name: research_agent
    package: research_agent  # resolved via register_agent_factory
    max_iterations: 3
    dependencies: [t1]
```

### Run

```bash
ice build examples/research_writer.yaml --output examples/research_writer.json
ICE_API_TOKEN=dev-token ice push examples/research_writer.json --api http://localhost:8000 --token $ICE_API_TOKEN
ice run <blueprint_id> --api http://localhost:8000 --token $ICE_API_TOKEN --input topic="renewable energy"
```

Acceptance
- Agent selects `lookup_tool`, then `writer_tool`, updates `context['agent']`, and finishes with a summary.
