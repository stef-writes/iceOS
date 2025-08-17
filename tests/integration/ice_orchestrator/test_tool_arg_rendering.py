from __future__ import annotations

from typing import Any, Dict

import pytest

from ice_core.models.mcp import Blueprint, NodeSpec
from ice_orchestrator.services.workflow_execution_service import (
    WorkflowExecutionService,
)

pytestmark = pytest.mark.asyncio

# Define tool at module scope so registry can import the factory by module:function
from ice_core.base_tool import ToolBase


class FakeTool(ToolBase):
    name: str = "fake_tool"

    async def _execute_impl(self, *, query: str) -> Dict[str, Any]:  # type: ignore[override]
        return {"answer": f"answered: {query}"}


def create_fake_tool() -> ToolBase:
    return FakeTool()


async def test_tool_args_are_jinja_rendered_and_filtered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tool args should render with Jinja and only accepted kwargs passed to _execute_impl."""

    from ice_core.unified_registry import register_tool_factory

    register_tool_factory("fake_tool", __name__ + ":create_fake_tool")

    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="{{ inputs.topic }}",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            output_schema={"text": "string"},
        ),
        NodeSpec(
            id="t1",
            type="tool",
            tool_name="fake_tool",
            tool_args={"query": "From LLM: {{ llm1.response }}"},
            dependencies=["llm1"],
        ),
    ]
    bp = Blueprint(nodes=nodes)

    # Stub LLM to avoid network and raise token ceiling to avoid guard
    from ice_core.llm import service as llm_service_mod
    from ice_orchestrator import config as orch_config

    async def fake_generate(*args: Any, **kwargs: Any):
        return kwargs.get("prompt", ""), None, None

    monkeypatch.setattr(llm_service_mod.LLMService, "generate", fake_generate)
    monkeypatch.setattr(orch_config.runtime_config, "max_tokens", 1_000_000)

    result = await WorkflowExecutionService().execute_blueprint(
        bp.nodes, inputs={"topic": "Deep Dive"}
    )
    assert result.success is True
    tool_out = result.output["t1"]
    assert tool_out["answer"] == "answered: From LLM: Deep Dive"
