from __future__ import annotations

"""Deterministic end-to-end runtime verification.

This script verifies three core flows without any external dependencies:

- LLM node (templating + provider call path)
- LLM → Tool (DAG dependency + Jinja arg rendering + signature filtering)
- Agent → Tool (plan→act loop via AgentRuntime with allowed_tools)

What it does:
- Registers an echo LLM under the model id used by NodeSpecs ("gpt-4o")
- Registers a simple writer_tool via the public registry factory API
- Lifts the token ceiling guard to avoid unrelated failures
- Executes small blueprints using WorkflowExecutionService

Usage:
    python scripts/verify_runtime.py

Expected:
- success=True for LLM-only and LLM→Tool runs
- Agent → Tool yields a dict with last_tool and the tool result

Note:
This runs entirely in-process and offline; it does not need network keys.
"""

import asyncio
from typing import Any, Dict, Optional, Tuple

from ice_core.base_tool import ToolBase
from ice_core.models.mcp import Blueprint, NodeSpec
from ice_core.unified_registry import register_llm_factory, register_tool_factory
from ice_orchestrator.config import runtime_config
from ice_orchestrator.services.agent_runtime import AgentRuntime
from ice_orchestrator.services.workflow_execution_service import (
    WorkflowExecutionService,
)


# --- Test LLM factory (echo) -------------------------------------------------
class _EchoLLM:
    async def generate(
        self,
        *,
        llm_config: Any,
        prompt: str,
        context: Dict[str, Any],
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        return (
            f"ECHO::{prompt}",
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            None,
        )


def create_echo_llm() -> _EchoLLM:
    return _EchoLLM()


# --- Test Tool factory -------------------------------------------------------
class _WriterTool(ToolBase):
    name: str = "writer_tool"

    async def _execute_impl(self, *, text: str) -> Dict[str, Any]:  # type: ignore[override]
        return {"written": text.upper()}


def create_writer_tool() -> ToolBase:
    return _WriterTool()


async def _run_llm_only() -> Dict[str, Any]:
    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="Hello {{ inputs.name }}",
            llm_config={"provider": "openai", "model": "gpt-4o"},
        )
    ]
    bp = Blueprint(nodes=nodes)
    svc = WorkflowExecutionService()
    res = await svc.execute_blueprint(bp.nodes, inputs={"name": "World"})
    return res.model_dump()  # type: ignore[no-any-return]


async def _run_llm_to_tool() -> Dict[str, Any]:
    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="{{ inputs.msg }}",
            llm_config={"provider": "openai", "model": "gpt-4o"},
        ),
        NodeSpec(
            id="t1",
            type="tool",
            tool_name="writer_tool",
            tool_args={"text": "{{ llm1.response }}"},
            dependencies=["llm1"],
        ),
    ]
    bp = Blueprint(nodes=nodes)
    svc = WorkflowExecutionService()
    res = await svc.execute_blueprint(bp.nodes, inputs={"msg": "ok"})
    return res.model_dump()  # type: ignore[no-any-return]


async def main() -> None:
    # Register echo LLM under the model name referenced in NodeSpec (gpt-4o)
    register_llm_factory("gpt-4o", __name__ + ":create_echo_llm")
    # Register writer tool
    register_tool_factory("writer_tool", __name__ + ":create_writer_tool")
    # Lift token ceiling for verification so guards don't interfere
    runtime_config.max_tokens = None

    print("=== LLM only ===")
    out1 = await _run_llm_only()
    print(out1)
    print("=== LLM → Tool ===")
    out2 = await _run_llm_to_tool()
    print(out2)

    # --- Agent → Tool -------------------------------------------------------
    class _SimpleAgent:
        def allowed_tools(self) -> list[str]:
            return ["writer_tool"]

        async def think(self, context: Dict[str, Any]) -> str:
            return "plan"

        def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "tool": "writer_tool",
                "inputs": {"text": "agent hello"},
                "done": True,
                "message": "acting",
            }

    print("=== Agent → Tool ===")
    agent_out = await AgentRuntime().run(_SimpleAgent(), context={})
    print(agent_out)


if __name__ == "__main__":
    asyncio.run(main())
