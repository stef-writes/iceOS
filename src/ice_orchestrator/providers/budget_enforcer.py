"""Budget enforcement for iceOS runtime – relocated to orchestrator layer."""

import logging
from typing import Optional

from ice_orchestrator.config import runtime_config

logger = logging.getLogger(__name__)

class BudgetEnforcer:  # – runtime helper
    """Configurable budget enforcement for LLM calls and tool executions."""

    def __init__(
        self,
        org_budget_usd: Optional[float] = None,
        max_llm_calls: Optional[int] = None,
        max_tool_executions: Optional[int] = None,
        max_agent_calls: Optional[int] = None,
        max_workflow_executions: Optional[int] = None,
        max_code_executions: Optional[int] = None,
    ) -> None:
        import os

        # Monetary budget ----------------------------------------------------
        self.org_budget_usd: float | None
        if org_budget_usd is not None:
            self.org_budget_usd = org_budget_usd
        else:
            env_budget = os.getenv("ORG_BUDGET_USD")
            self.org_budget_usd = (
                float(env_budget) if env_budget else runtime_config.org_budget_usd
            )

        # Call/exec limits ----------------------------------------------------
        self.max_llm_calls = max_llm_calls or self._get_env_int("ICE_MAX_LLM_CALLS", 10)
        self.max_tool_executions = max_tool_executions or self._get_env_int(
            "ICE_MAX_TOOL_EXECUTIONS", 20
        )
        self.max_agent_calls = max_agent_calls or self._get_env_int("ICE_MAX_AGENT_CALLS", 5)
        self.max_workflow_executions = max_workflow_executions or self._get_env_int(
            "ICE_MAX_WORKFLOW_EXECUTIONS", 10
        )
        self.max_code_executions = max_code_executions or self._get_env_int(
            "ICE_MAX_CODE_EXECUTIONS", 15
        )

        # Runtime state -------------------------------------------------------
        self._llm_calls = 0
        self._tool_execs = 0
        self._agent_calls = 0
        self._workflow_execs = 0
        self._code_execs = 0
        self._total_cost = 0.0

        # Fail-open/closed behaviour -----------------------------------------
        env_fail_open = os.getenv("BUDGET_FAIL_OPEN")
        if env_fail_open is not None:
            self._fail_open = env_fail_open.lower() in {"1", "true", "yes", "on"}
        else:
            self._fail_open = runtime_config.budget_fail_open

        env_runtime_mode = os.getenv("ICE_RUNTIME_MODE")
        self._runtime_mode = env_runtime_mode or runtime_config.runtime_mode

        logger.info(
            "BudgetEnforcer initialized: org_budget=%.2f, max_llm=%d, max_tools=%d, max_agents=%d, mode=%s, fail_open=%s",
            self.org_budget_usd or 0.0,
            self.max_llm_calls,
            self.max_tool_executions,
            self.max_agent_calls,
            self._runtime_mode,
            self._fail_open,
        )

    # ---------------------------------------------------------------------
    def _get_env_int(self, key: str, default: int) -> int:
        import os

        value = os.getenv(key)
        return int(value) if value else default

    # --------------------------------------------------------------------- Public API
    def register_llm_call(self, cost: float = 0.0) -> None:
        self._llm_calls += 1
        self._total_cost += cost

        if self._llm_calls > self.max_llm_calls:
            self._handle_violation(
                "llm_calls",
                f"LLM call budget exceeded (max={self.max_llm_calls}, current={self._llm_calls})",
            )

        if self.org_budget_usd and self._total_cost > self.org_budget_usd:
            self._handle_violation(
                "cost",
                f"Cost budget exceeded (max=${self.org_budget_usd:.2f}, current=${self._total_cost:.2f})",
            )

    def register_tool_execution(self) -> None:
        self._tool_execs += 1
        if self._tool_execs > self.max_tool_executions:
            self._handle_violation(
                "tool_executions",
                f"Tool execution budget exceeded (max={self.max_tool_executions}, current={self._tool_execs})",
            )

    def register_agent_call(self, cost: float = 0.0) -> None:
        """Register an agent execution, which may include embedded LLM costs."""
        self._agent_calls += 1
        self._total_cost += cost
        
        if self._agent_calls > self.max_agent_calls:
            self._handle_violation(
                "agent_calls", 
                f"Agent call budget exceeded (max={self.max_agent_calls}, current={self._agent_calls})",
            )
            
        if self.org_budget_usd and self._total_cost > self.org_budget_usd:
            self._handle_violation(
                "cost",
                f"Cost budget exceeded (max=${self.org_budget_usd:.2f}, current=${self._total_cost:.2f})",
            )

    def register_workflow_execution(self) -> None:
        """Register a workflow execution."""
        self._workflow_execs += 1
        if self._workflow_execs > self.max_workflow_executions:
            self._handle_violation(
                "workflow_executions",
                f"Workflow execution budget exceeded (max={self.max_workflow_executions}, current={self._workflow_execs})",
            )

    def register_code_execution(self) -> None:
        """Register a code node execution."""
        self._code_execs += 1
        if self._code_execs > self.max_code_executions:
            self._handle_violation(
                "code_executions",
                f"Code execution budget exceeded (max={self.max_code_executions}, current={self._code_execs})",
            )

    # --------------------------------------------------------------------- helpers
    def _handle_violation(self, _type: str, message: str) -> None:
        logger.warning("Budget violation: %s", message)
        should_fail_closed = self._runtime_mode == "production" or not self._fail_open
        if should_fail_closed:
            raise RuntimeError(f"Budget violation: {message}")
        logger.info(
            "Budget violation in %s mode with fail-open enabled - continuing execution",
            self._runtime_mode,
        )

    # --------------------------------------------------------------------- properties
    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    @property
    def tool_execs(self) -> int:
        return self._tool_execs

    @property
    def agent_calls(self) -> int:
        return self._agent_calls

    @property
    def workflow_execs(self) -> int:
        return self._workflow_execs

    @property  
    def code_execs(self) -> int:
        return self._code_execs

    @property
    def total_cost(self) -> float:
        return self._total_cost

    def get_status(self) -> dict[str, float | int | bool | str | None]:
        return {
            "llm_calls": self._llm_calls,
            "tool_executions": self._tool_execs,
            "agent_calls": self._agent_calls,
            "workflow_executions": self._workflow_execs,
            "code_executions": self._code_execs,
            "total_cost": self._total_cost,
            "max_llm_calls": self.max_llm_calls,
            "max_tool_executions": self.max_tool_executions,
            "max_agent_calls": self.max_agent_calls,
            "max_workflow_executions": self.max_workflow_executions,
            "max_code_executions": self.max_code_executions,
            "org_budget_usd": self.org_budget_usd,
            "runtime_mode": self._runtime_mode,
            "fail_open": self._fail_open,
        }
