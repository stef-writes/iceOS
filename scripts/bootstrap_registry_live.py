"""Bootstrap registry with live-mode tool instances.
Run once per new interpreter (before demos) if you don't want to restart the shell.
"""

from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry
from ice_tools.toolkits.ecommerce.listing_agent import ListingAgentTool
from ice_tools.toolkits.ecommerce.title_description_generator import (
    TitleDescriptionGeneratorTool,
)

registry._instances.setdefault(NodeType.TOOL, {})
registry._instances[NodeType.TOOL][TitleDescriptionGeneratorTool.name] = (
    TitleDescriptionGeneratorTool(test_mode=False)
)
registry._instances[NodeType.TOOL][ListingAgentTool.name] = ListingAgentTool(
    test_mode=False, upload=True
)
print("Registry bootstrapped with live instances.")
