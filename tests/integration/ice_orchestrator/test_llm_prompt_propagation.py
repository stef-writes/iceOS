from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from ice_core.models.mcp import Blueprint, NodeSpec
from ice_orchestrator.services.workflow_execution_service import (
    WorkflowExecutionService,
)

pytestmark = pytest.mark.asyncio


async def test_llm_prompt_is_rendered_and_propagated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm2.prompt = "{{ llm1.response }}" should render fully and match llm1.response.

    We stub the provider layer to avoid network and to ensure deterministic text.
    """

    # Stub LLMService.generate to return predictable text and usage
    from ice_core.llm import service as llm_service_mod

    async def fake_generate(
        *args: Any, **kwargs: Any
    ) -> tuple[str, Dict[str, int] | None, str | None]:
        prompt = kwargs.get("prompt", "")
        # Echo a deterministic response per prompt to validate propagation
        return (
            f"ECHO::{prompt}",
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            None,
        )

    monkeypatch.setattr(llm_service_mod.LLMService, "generate", fake_generate)

    # Blueprint: llm1 → llm2 where llm2.prompt references llm1.response via Jinja
    nodes = [
        NodeSpec(
            id="llm1",
            type="llm",
            model="gpt-4o",
            prompt="Hello {{ inputs.name }}",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            output_schema={"text": "string"},
        ),
        NodeSpec(
            id="llm2",
            type="llm",
            model="gpt-4o",
            prompt="{{ llm1.response }}",
            llm_config={"provider": "openai", "model": "gpt-4o"},
            output_schema={"text": "string"},
            dependencies=["llm1"],
        ),
    ]
    bp = Blueprint(nodes=nodes)

    # Increase token ceiling to avoid token guard interfering in this test
    from ice_orchestrator import config as orch_config

    monkeypatch.setattr(orch_config.runtime_config, "max_tokens", 1_000_000)

    svc = WorkflowExecutionService()
    result = await svc.execute_blueprint(bp.nodes, inputs={"name": "World"})

    assert result.success is True
    assert isinstance(result.output, dict)
    llm1_out = result.output["llm1"]["response"]
    llm2_prompt = result.output["llm2"]["prompt"]
    # llm1 echo should have the rendered prompt already
    assert llm1_out.startswith("ECHO::")
    # llm2 prompt must be the rendered llm1.response (no braces)
    assert "{" not in llm2_prompt and "}" not in llm2_prompt
    assert llm2_prompt == llm1_out
