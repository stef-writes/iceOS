"""Agent factory for ScriptChain execution.

Builds :class:`AgentNode` instances from **LLMOperatorConfig** nodes while
respecting chain-level and global skill precedence.
"""

from __future__ import annotations

# NOTE: Use AgentNode from ice_sdk to avoid dependency on ice_core
from typing import TYPE_CHECKING, Dict, List

from ice_sdk.agents import AgentNode  # runtime import
from ice_sdk.skills.base import SkillBase

# ------------------------------------------------------------------
# Backwards-compatibility: *BaseTool* alias -------------------------
# ------------------------------------------------------------------


if TYPE_CHECKING:  # pragma: no cover
    # Type-checking imports using SDK alias to avoid cross-layer dependency
    from ice_core.models.agent_models import AgentConfig, ModelSettings
    from ice_core.models.node_models import LLMOperatorConfig

    from ice_sdk import AgentNode
    from ice_sdk.context import GraphContextManager


class AgentFactory:  # noqa: D101 – internal utility
    """Factory for creating AgentNode instances from LLMOperatorConfig."""

    def __init__(
        self, context_manager: "GraphContextManager", chain_skills: List["SkillBase"]
    ) -> None:
        self.context_manager = context_manager
        self.chain_skills = chain_skills

    def make_agent(self, node: "LLMOperatorConfig") -> "AgentNode":
        """Convert an *LLMOperatorConfig* into a fully-initialised :class:`AgentNode`.

        The method builds a tool map with proper precedence:
        1. Globally registered tools (lowest precedence)
        2. Chain-level tools – override globals when name clashes
        3. Node-specific tool refs override everything else
        """

        # Build tool map so later inserts override earlier ones (priority)
        tool_map: Dict[str, "SkillBase"] = {}

        # 1. Globally registered tools (lowest precedence) --------------
        for name, tool in self.context_manager.get_all_tools().items():
            tool_map[name] = tool

        # 2. Chain-level tools – override globals when name clashes ------
        for t in self.chain_skills:
            tool_map[t.name] = t

        # 3. Node-specific tool refs override everything else -----------
        for cfg in getattr(node, "tools", None) or []:  # type: ignore[attr-defined]
            t_obj = self.context_manager.get_tool(cfg.name)
            if t_obj is not None:
                tool_map[t_obj.name] = t_obj

        tools: List["SkillBase"] = list(tool_map.values())

        # Build AgentConfig ----------------------------------------------
        model_settings = ModelSettings(
            model=node.model,
            temperature=getattr(node, "temperature", 0.7),
            max_tokens=getattr(node, "max_tokens", None),
            provider=str(getattr(node.provider, "value", node.provider)),
        )

        agent_cfg = AgentConfig(
            name=node.name or node.id,
            instructions=node.prompt,
            model=node.model,
            model_settings=model_settings,
            tools=tools,
        )  # type: ignore[call-arg]

        agent = AgentNode(config=agent_cfg, context_manager=self.context_manager)
        agent.tools = tools  # expose on instance (used by AgentNode.execute)

        # ------------------------------------------------------------------
        # Register agent & tools with the ContextManager -------------------
        # ------------------------------------------------------------------
        try:
            self.context_manager.register_agent(agent)
        except ValueError:
            # Already registered – ignore duplicate
            pass

        for tool in tools:
            try:
                self.context_manager.register_tool(tool)
            except ValueError:
                # Possible duplicate registration – safe to ignore
                continue

        return agent
