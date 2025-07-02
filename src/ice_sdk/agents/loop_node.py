from __future__ import annotations

from typing import Any, Dict, Optional

from ..models.node_models import NodeExecutionResult
from .agent_node import AgentNode


class LoopNode(AgentNode):
    """Agent node that can self-iterate (LangGraph-style) until a guard limit.

    The default implementation simply executes the underlying *AgentNode* logic
    repeatedly.  Advanced planning (emitting new nodes, tool calls, etc.) can
    be layered on top without changing the orchestrator.
    """

    def __init__(
        self,
        *args: Any,
        max_iters: int = 5,
        cost_budget: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.max_iters = max_iters
        self.cost_budget = cost_budget

    async def execute(self, input: Dict[str, Any]) -> NodeExecutionResult:  # type: ignore[override]
        remaining = self.max_iters
        total_cost = 0.0
        latest: Optional[NodeExecutionResult] = None

        while remaining > 0:
            latest = await super().execute(input)
            remaining -= 1

            # Cost tracking -------------------------------------------------
            if latest.usage and latest.usage.cost:
                total_cost += latest.usage.cost
                if self.cost_budget and total_cost > self.cost_budget:
                    break

            # Simple heuristic – break when agent returns plain text answer
            if latest.success and isinstance(latest.output, str):
                break

            # TODO: update *input* from scratchpad/memory here if needed.

        return latest if latest is not None else await super().execute(input)
