"""Agent factory for ScriptChain execution.

Builds :class:`AgentNode` instances from **LLMOperatorConfig** nodes while
respecting chain-level and global tool precedence.
"""

from __future__ import annotations

# NOTE: Use AgentNode from ice_sdk to avoid dependency on ice_core
from typing import TYPE_CHECKING, Dict, List

from ice_core.models.llm import LLMConfig
from ice_sdk.agents import AgentNode, AgentNodeConfig  # runtime import
from ice_sdk.tools.base import ToolBase

# ------------------------------------------------------------------
# Backwards-compatibility: *BaseTool* alias -------------------------
# ------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover
    # Type-checking imports using SDK alias to avoid cross-layer dependency
    from ice_core.models.llm import LLMConfig
    from ice_core.models.node_models import LLMOperatorConfig
    from ice_sdk import AgentNode
    from ice_sdk.agents.agent_node import AgentNodeConfig
    from ice_sdk.context import GraphContextManager

class AgentFactory:  # – internal utility
    """Factory for creating AgentNode instances from LLMOperatorConfig."""

    def __init__(
        self, context_manager: "GraphContextManager", chain_tools: List["ToolBase"]
    ) -> None:
        self.context_manager = context_manager
        self.chain_tools = chain_tools

    def make_agent(self, node: "LLMOperatorConfig") -> "AgentNode":
        """Convert an *LLMOperatorConfig* into a fully-initialised :class:`AgentNode`.

        The method builds a tool map with proper precedence:
        1. Globally registered tools (lowest precedence)
        2. Chain-level tools – override globals when name clashes
        3. Node-specific tool refs override everything else
        """

        # Build tool map so later inserts override earlier ones (priority)
        tool_map: Dict[str, "ToolBase"] = {}

        # 1. Globally registered tools (lowest precedence) --------------
        for name, tool in self.context_manager.get_all_tools().items():
            tool_map[name] = tool

        # 2. Chain-level tools – override globals when name clashes ------
        for t in self.chain_tools:
            tool_map[t.name] = t

        # 3. Node-specific tool refs override everything else -----------
        for cfg in getattr(node, "tools", None) or []:  # type: ignore[attr-defined]
            t_obj = self.context_manager.get_tool(cfg.name)
            if t_obj is not None:
                tool_map[t_obj.name] = t_obj

        tools: List["ToolBase"] = list(tool_map.values())

        # Build AgentConfig ----------------------------------------------
        llm_cfg = LLMConfig(provider=node.provider)  # minimal mapping

        agent_cfg = AgentNodeConfig(  # type: ignore[call-arg]
            llm_config=llm_cfg,
            system_prompt=node.prompt,
            tools=[t.name for t in tools],
        )

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
