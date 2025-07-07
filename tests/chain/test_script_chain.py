from __future__ import annotations

from typing import Any

import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.config import LLMConfig, ModelProvider
from ice_sdk.models.node_models import AiNodeConfig, ToolNodeConfig
from ice_sdk.providers.llm_service import LLMService
from ice_sdk.tools.base import BaseTool


class EchoTool(BaseTool):
    """Simple echo tool used in integration tests."""

    name = "echo_test"
    description = "Echo tool – returns input verbatim"

    async def run(self, **kwargs: Any):  # type: ignore[override]
        kwargs.pop("ctx", None)  # remove non-serialisable context
        return {"echo": kwargs}


@pytest.mark.asyncio
async def test_script_chain_ai_and_tool(monkeypatch):
    """End-to-end check: ScriptChain executes a tool node and an ai node."""

    # ------------------------------------------------------------------
    # 1. Monkey-patch LLMService.generate so no network call happens
    # ------------------------------------------------------------------
    async def _fake_generate(  # noqa: D401
        self: LLMService,  # noqa: D401 – signature must accept self
        llm_config: LLMConfig,  # noqa: D401
        prompt: str,  # noqa: D401
        context: dict[str, Any] | None = None,  # noqa: D401
        tools=None,  # noqa: D401
        **_kwargs: Any,  # noqa: D401
    ):
        # Return deterministic JSON payload recognised by AgentNode
        return (
            "OK",
            {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            None,
        )

    monkeypatch.setattr(LLMService, "generate", _fake_generate, raising=False)

    # ------------------------------------------------------------------
    # 2. Build node configs
    # ------------------------------------------------------------------
    tool_cfg = ToolNodeConfig(
        id="tool1",
        name="EchoTool",
        tool_name="echo_test",
    )

    ai_cfg = AiNodeConfig(
        id="ai1",
        name="Agent",
        model="gpt-3.5-turbo",
        prompt="Return OK",
        llm_config=LLMConfig(provider=ModelProvider.OPENAI, model="gpt-3.5-turbo"),
        dependencies=["tool1"],
    )

    echo_tool = EchoTool()

    chain = ScriptChain(
        nodes=[tool_cfg, ai_cfg],
        tools=[echo_tool],
        name="integ_test_chain",
        initial_context={"seed": 1},
    )

    # ------------------------------------------------------------------
    # 3. Execute & assert ------------------------------------------------
    # ------------------------------------------------------------------
    result = await chain.execute()

    assert result.success is True
    # The chain should produce at least two node results
    assert result.output is not None
    assert set(result.output.keys()) == {"tool1", "ai1"}
    assert result.output["tool1"].success is True
    assert result.output["ai1"].success is True
