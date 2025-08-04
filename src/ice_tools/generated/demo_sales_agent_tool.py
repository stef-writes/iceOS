"""Tool wrapper exposing agent `demo_sales_agent` as a tool."""

from __future__ import annotations
from typing import Any, Dict, List

from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry, global_agent_registry

class DemoSalesAgentAgentTool(ToolBase):
    name: str = "agent_tool::demo_sales_agent"
    description: str = "Agent wrapper tool"

    async def _execute_impl(self, *, messages: List[Dict[str, str]]) -> Dict[str, Any]:  # noqa: D401
        AgentCls = global_agent_registry.get_agent_class("demo_sales_agent")
        agent = AgentCls()
        reply = await agent.run(messages=messages)
        return {"reply": reply}

_instance = DemoSalesAgentAgentTool()
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)
