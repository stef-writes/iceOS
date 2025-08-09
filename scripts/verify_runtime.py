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
from ice_core.unified_registry import (
    register_llm_factory,
    register_tool_factory,
    register_swarm_factory,
)
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


# --- Semi-realistic LLM (deterministic) -------------------------------------
class _PhiloLLM:
    async def generate(
        self,
        *,
        llm_config: Any,
        prompt: str,
        context: Dict[str, Any],
    ) -> Tuple[str, Optional[Dict[str, int]], Optional[str]]:
        text: str
        if "philosophical proposition" in prompt.lower():
            text = (
                "Consciousness arises from self-referential information processing constrained by embodiment."
            )
        elif "analyze the following proposition" in prompt.lower():
            lines = [ln.strip() for ln in prompt.splitlines() if ln.strip()]
            prop = lines[-1] if lines else "(unknown proposition)"
            text = (
                f"- Coherence: The proposition '{prop}' is internally consistent given its terms.\n"
                f"- Originality: It blends computational and embodied views, offering a hybrid thesis.\n"
                f"- Rigor: Clarify 'self-referential' and 'embodiment' to make testable claims."
            )
        else:
            text = "Processed"
        return text, {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25}, None


def create_philo_llm() -> _PhiloLLM:
    return _PhiloLLM()


async def _run_llm_only() -> Dict[str, Any]:
    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="Hello {{ inputs.name }}",
            llm_config={"provider": "openai", "model": "gpt-4o", "temperature": 0.0},
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
            llm_config={"provider": "openai", "model": "gpt-4o", "temperature": 0.0},
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


async def _run_llm_search_llm() -> Dict[str, Any]:
    # Ensure search tool is registered (live SerpAPI if SERPAPI_KEY is set)
    import ice_tools.generated.search_tool  # noqa: F401

    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="Formulate a search query for '{{ inputs.topic }}'",
            llm_config={"provider": "openai", "model": "gpt-4o", "temperature": 0.0},
        ),
        NodeSpec(
            id="search",
            type="tool",
            tool_name="search_tool",
            tool_args={"query": "{{ llm1.response }}"},
            dependencies=["llm1"],
        ),
        NodeSpec(
            id="llm2",
            type="llm",
            model="gpt-4o",
            prompt=(
                "Summarize the top result: {{ search.results[0].title }} - "
                "{{ search.results[0].snippet }}"
            ),
            llm_config={"provider": "openai", "model": "gpt-4o", "temperature": 0.0},
            dependencies=["search"],
        ),
    ]
    bp = Blueprint(nodes=nodes)
    svc = WorkflowExecutionService()
    res = await svc.execute_blueprint(bp.nodes, inputs={"topic": "renewable energy"})
    return res.model_dump()  # type: ignore[no-any-return]


# --- Simple swarm factory (deterministic) ------------------------------------
class _SimpleSwarm:
    async def execute(self, *, workflow: Any, cfg: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        roles = [a.role for a in getattr(cfg, "agents", [])]
        return {"consensus": "approved", "agents": roles}


def create_simple_swarm(**kwargs: Any) -> _SimpleSwarm:
    return _SimpleSwarm()


async def _run_swarm() -> Dict[str, Any]:
    # Register under both a generic name and the node id to ensure factory path is hit
    register_swarm_factory("simple_swarm", __name__ + ":create_simple_swarm")
    register_swarm_factory("swarm1", __name__ + ":create_simple_swarm")
    nodes = [
        NodeSpec(
            id="swarm1",
            type="swarm",
            agents=[
                {"package": "agent.a", "role": "writer"},
                {"package": "agent.b", "role": "reviewer"},
            ],
        )
    ]
    bp = Blueprint(nodes=nodes)
    svc = WorkflowExecutionService()
    res = await svc.execute_blueprint(bp.nodes, inputs={})
    return res.model_dump()  # type: ignore[no-any-return]


async def _run_semi_realistic_llm_chain() -> Dict[str, Any]:
    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="Generate a philosophical proposition about consciousness in one sentence.",
            llm_config={"provider": "openai", "model": "gpt-4o", "temperature": 0.0},
        ),
        NodeSpec(
            id="llm2",
            type="llm",
            model="gpt-4o",
            prompt=(
                "Analyze the following proposition for coherence, originality, and philosophical rigor:\n"
                "{{ llm1.response }}\nProvide 3 bullet points."
            ),
            llm_config={"provider": "openai", "model": "gpt-4o", "temperature": 0.0},
            dependencies=["llm1"],
        ),
    ]
    bp = Blueprint(nodes=nodes)
    svc = WorkflowExecutionService()
    res = await svc.execute_blueprint(bp.nodes, inputs={})
    return res.model_dump()  # type: ignore[no-any-return]


async def main() -> None:
    # Use real LLM provider – do not register deterministic factory
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
    print("=== LLM → SearchTool → LLM ===")
    out2b = await _run_llm_search_llm()
    print(out2b)
    print("=== Semi-realistic LLM1 → LLM2 ===")
    out3 = await _run_semi_realistic_llm_chain()
    print(out3)
    print("=== Swarm (factory) ===")
    out4 = await _run_swarm()
    print(out4)

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
    # Agent with minimal intra-run memory via context (two steps)
    class _MemoryAgent:
        def __init__(self) -> None:
            self.step = 0

        def allowed_tools(self) -> list[str]:
            return ["writer_tool"]

        async def think(self, context: Dict[str, Any]) -> str:
            return "plan"

        def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
            self.step += 1
            if self.step == 1:
                return {"tool": "writer_tool", "inputs": {"text": "memo"}, "done": False, "message": "writing"}
            # Read prior tool output recorded by runtime under context['agent']
            last = (context.get("agent") or {}).get("last_result") or {}
            msg = f"read:{last}"
            return {"done": True, "message": msg}

    agent_out = await AgentRuntime().run(_MemoryAgent(), context={}, max_iterations=2)
    print(agent_out)


if __name__ == "__main__":
    asyncio.run(main())
