from __future__ import annotations

from typing import Any, Dict

import pytest

from ice_sdk.agents.agent_node import AgentNode
from ice_sdk.context.manager import GraphContextManager
from ice_sdk.models.agent_models import AgentConfig, ModelSettings
from ice_sdk.models.config import LLMConfig
from ice_sdk.models.node_models import NodeExecutionResult, NodeMetadata
from ice_sdk.providers.llm_service import LLMService


class PassiveAgent(AgentNode):
    """A deterministic agent that just returns its *name* in the output."""

    def __init__(self, name: str, ctx_mgr: GraphContextManager):
        cfg = AgentConfig(
            name=name,
            instructions="You are a passive agent",
            model="gpt-3.5-turbo",
            model_settings=ModelSettings(model="gpt-3.5-turbo", temperature=0.0, provider="openai"),
            tools=[],
        )
        super().__init__(config=cfg, context_manager=ctx_mgr)

    async def execute(self, input: Dict[str, Any]):  # type: ignore[override]
        meta = NodeMetadata(node_id=self.config.name, node_type="agent")  # type: ignore[arg-type]
        return NodeExecutionResult(success=True, output={"agent": self.config.name}, metadata=meta)


class RouterAgent(AgentNode):
    """Agent that routes to a target agent as instructed by LLMService.generate."""

    async def execute(self, input: Dict[str, Any]):  # type: ignore[override]
        # Ask LLM which agent to call (stubbed in test)
        target_name, _, _ = await self.llm_service.generate(  # type: ignore[attr-defined]
            llm_config=LLMConfig(provider="openai", model="gpt-3.5-turbo"),
            prompt="choose agent",
            context={},
            tools=None,
        )

        target = self.context_manager.get_agent(target_name)
        assert target is not None, f"Target agent '{target_name}' not registered"
        return await target.execute(input)


@pytest.mark.asyncio
async def test_router_agent_forwards(monkeypatch):
    ctx_mgr = GraphContextManager()

    # Register passive agents ------------------------------------------------
    alpha = PassiveAgent("alpha", ctx_mgr)
    beta = PassiveAgent("beta", ctx_mgr)
    ctx_mgr.register_agent(alpha)
    ctx_mgr.register_agent(beta)

    # Build router agent -----------------------------------------------------
    router_cfg = AgentConfig(
        name="router",
        instructions="Route to the correct agent",
        model="gpt-3.5-turbo",
        model_settings=ModelSettings(model="gpt-3.5-turbo", temperature=0.0, provider="openai"),
        tools=[],
    )
    llm_service = LLMService()
    router = RouterAgent(config=router_cfg, context_manager=ctx_mgr, llm_service=llm_service)

    # Monkeypatch LLMService.generate to always pick "beta" ------------------
    async def _fake_generate(*_args, **_kwargs):  # noqa: D401
        return "beta", None, None

    monkeypatch.setattr(llm_service, "generate", _fake_generate, raising=True)

    result = await router.execute({"foo": "bar"})

    assert result.success
    assert result.output == {"agent": "beta"} 