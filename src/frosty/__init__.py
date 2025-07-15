"""
iceOS Frosty - Meta-agent layer for building workflows

Frosty is the AI specialist that converts user intent into executable
workflows by generating tools, nodes, and chains using the iceOS SDK.

Key components:
- agents: FlowDesignAgent, NodeBuilderAgent, ToolForgeAgent
- tools: Meta-tools for building other tools
- core: Context, memory, and planning systems
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .context import FrostyContext

__all__ = [
    # Core
    "FrostyContext",
    "FrostyCLI",
    # Agents (lazily loaded)
    "FlowDesignAgent",
    "NodeBuilderAgent",
    "ToolForgeAgent",
]

# ---------------------------------------------------------------------------
# Lazy attribute loader – keeps import time low and avoids hard deps
# ---------------------------------------------------------------------------

_AGENT_MAP = {
    "FlowDesignAgent": "agents.flow_design.assistant",
    "NodeBuilderAgent": "agents.node_builder.builder",
    "ToolForgeAgent": "agents.tool_forge.forge",
}


def __getattr__(name: str) -> Any:  # pragma: no cover – dynamic path
    if name in _AGENT_MAP:
        module = import_module(f".{_AGENT_MAP[name]}", __name__)
        return getattr(module, name)
    raise AttributeError(name)


# ---------------------------------------------------------------------------
# Minimal FrostyCLI stub – enough to satisfy open-source tests
# ---------------------------------------------------------------------------


class FrostyCLI:  # noqa: D101 – simple stub
    def __init__(self) -> None:
        self.context: FrostyContext | None = None

    async def _init_frosty(self) -> None:  # noqa: D401 – test helper
        """Initialise the context and register default stub agents."""

        if self.context is not None:
            return

        from . import FlowDesignAgent, NodeBuilderAgent, ToolForgeAgent  # lazy
        from .agents.chain_tester.tester import ChainTesterAgent
        from .agents.prompt_engineer.optimiser import (  # noqa: WPS433 – local import fine in stub
            PromptEngineerAgent,
        )

        self.context = FrostyContext()

        await self.context.register_agent("flow_design", FlowDesignAgent())
        await self.context.register_agent("node_builder", NodeBuilderAgent())
        await self.context.register_agent("tool_forge", ToolForgeAgent())
        await self.context.register_agent("prompt_engineer", PromptEngineerAgent())
        await self.context.register_agent("chain_tester", ChainTesterAgent())

    # ------------------------------------------------------------------
    async def _list_agents(self) -> None:  # noqa: D401 – stub
        if self.context is None:
            await self._init_frosty()
        assert self.context is not None
        for name in self.context.agents:
            print(f"• {name}")

    async def _health_check(self) -> None:  # noqa: D401 – stub
        if self.context is None:
            await self._init_frosty()
        assert self.context is not None
        await self.context.validate()
        summary = await self.context.guardrails.get_usage_summary()
        print("context=valid", summary)


# ---------------------------------------------------------------------------
# Type-checker friendliness – reveal symbols when analysing
# ---------------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover
    from .agents.flow_design.assistant import FlowDesignAgent as FlowDesignAgent
    from .agents.node_builder.builder import NodeBuilderAgent as NodeBuilderAgent
    from .agents.tool_forge.forge import ToolForgeAgent as ToolForgeAgent
