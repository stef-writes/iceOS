from __future__ import annotations

"""BudgetAdvisorAgent – trivial demo agent that echoes advice."""

from typing import Any, Dict

from ice_sdk.registry.agent import global_agent_registry


class BudgetAdvisorAgent:
    name = "budget_advisor"

    def validate(self):
        pass

    async def execute(self, inputs: Dict[str, Any]):  # noqa: D401 – demo
        amount = inputs.get("amount", 0)
        return {"advice": f"Consider reducing discretionary spending to save ${amount * 0.1:.2f}"}


# Register

global_agent_registry.register("budget_advisor", BudgetAdvisorAgent()) 