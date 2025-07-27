"""Agent factory for workflow execution - DEPRECATED.

This factory was used to auto-upgrade LLM nodes with tools to Agent nodes.
Since LLM nodes no longer support tools, this factory should not be used.
Users should explicitly create AgentNodeConfig for any LLM+tools use case.

TODO: Remove this factory entirely once all references are cleaned up.
"""

from __future__ import annotations

# NOTE: Use AgentNode from ice_sdk to avoid dependency on ice_core
from typing import TYPE_CHECKING, Dict, List

from ice_core.models.llm import LLMConfig
from ice_orchestrator.agent import AgentNode  # local import
from ice_core.models.node_models import AgentNodeConfig
from ice_core.base_tool import ToolBase

# ------------------------------------------------------------------
# Backwards-compatibility: *BaseTool* alias -------------------------
# ------------------------------------------------------------------

if TYPE_CHECKING:  # pragma: no cover
    # Type-checking imports
    from ice_core.models.llm import LLMConfig
    from ice_core.models.node_models import LLMOperatorConfig, AgentNodeConfig
    from ice_orchestrator.agent import AgentNode
    from ice_orchestrator.context import GraphContextManager

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

        # NOTE: LLM nodes no longer have tools - removed this check

        tools: List["ToolBase"] = list(tool_map.values())

        # Build AgentConfig ----------------------------------------------
        llm_cfg = LLMConfig(provider=node.provider, model=node.model)

        # Create proper AgentNodeConfig with required fields
        from ice_core.models.node_models import ToolConfig
        tool_configs = [ToolConfig(name=t.name) for t in tools]
        
        agent_cfg = AgentNodeConfig(
            id=node.id,
            type="agent",
            package="ice_orchestrator.agent",  # Using built-in agent
            llm_config=llm_cfg,
            tools=tool_configs,
            agent_config={
                "system_prompt": node.prompt,
                "max_retries": 3,
            }
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
