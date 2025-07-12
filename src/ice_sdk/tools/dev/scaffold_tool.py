"""Development scaffolding tools for node creation and tool discovery."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

import yaml
from pydantic import BaseModel

from ..base import function_tool as tool

# ---------------------------------------------------------------------------
# Temporary placeholder until full config validation is implemented -----------
# ---------------------------------------------------------------------------

# pragma: no cover – placeholder module not yet production-ready


def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401 – minimal stub
    """Return *cfg* unchanged (placeholder until real validation)."""
    return cfg


@tool()
async def suggest_existing_tools(user_requirement: str) -> str:
    """Search registered tools matching a use case"""
    # Uses ice_sdk.capabilities.registry
    return "Similar tools: ResearchTool, DataVizTool, WebhookTool"


@tool()
async def generate_node_stub(config: Dict[str, Any]) -> str:
    """Create ainode.yaml scaffold"""
    # Uses schemas/runtime/AiNodeConfig.json
    return yaml.dump(validate_config(config))


class NodeScaffoldRequest(BaseModel):
    node_type: Literal["AI", "Tool", "Conditional"]
    requirements: str


@tool()
async def generate_node_scaffold(request: NodeScaffoldRequest) -> Dict[str, Any]:
    """Generates node configuration scaffold based on type"""
    base_config = {
        "apiVersion": "iceos/v1alpha1",
        "kind": "AiNode" if request.node_type == "AI" else "ToolNode",
        "requirements": request.requirements.split(","),
    }
    return validate_config(base_config)


@tool()
async def visualize_chain(nodes: List[str]) -> str:
    """Generates Mermaid diagram code for proposed flow"""
    return "graph TD\n\t" + "\n\t".join(nodes)
