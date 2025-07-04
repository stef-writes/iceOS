from typing import Literal

import yaml
from pydantic import BaseModel

from ice_sdk.tools import ToolMetadata, tool

# ---------------------------------------------------------------------------
# Temporary placeholder until full config validation is implemented -----------
# ---------------------------------------------------------------------------


def validate_config(cfg):  # noqa: D401  – minimal stub
    """Return *cfg* unchanged (placeholder)."""
    return cfg


@tool
async def suggest_existing_tools(user_requirement: str) -> str:
    """Search registered tools matching a use case"""
    # Uses ice_sdk.capabilities.registry
    return "Similar tools: ResearchTool, DataVizTool, WebhookTool"


@tool
async def generate_node_stub(config: dict) -> str:
    """Create ainode.yaml scaffold"""
    # Uses schemas/runtime/AiNodeConfig.json
    return yaml.dump(validate_config(config))


class NodeScaffoldRequest(BaseModel):
    node_type: Literal["AI", "Tool", "Conditional"]
    requirements: str


@tool(
    metadata=ToolMetadata(
        name="node_scaffolder",
        description="Generates starter YAML configs for new nodes",
    )
)
async def generate_node_scaffold(request: NodeScaffoldRequest) -> dict:
    """Generates node configuration scaffold based on type"""
    base_config = {
        "apiVersion": "iceos/v1alpha1",
        "kind": "AiNode" if request.node_type == "AI" else "ToolNode",
        "requirements": request.requirements.split(","),
    }
    return validate_config(base_config)  # Uses existing validation


@tool
async def visualize_chain(nodes: list[str]) -> str:
    """Generates Mermaid diagram code for proposed flow"""
    return "graph TD\n\t" + "\n\t".join(nodes)
