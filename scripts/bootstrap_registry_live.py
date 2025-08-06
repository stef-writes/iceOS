"""Bootstrap registry with live-mode tool instances.
Run once per new interpreter (before demos) if you don't want to restart the shell.
"""
from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType
from ice_tools.toolkits.ecommerce.title_description_generator import TitleDescriptionGeneratorTool
from ice_tools.toolkits.ecommerce.listing_agent import ListingAgentTool

registry._instances.setdefault(NodeType.TOOL, {})
registry._instances[NodeType.TOOL][TitleDescriptionGeneratorTool.name] = TitleDescriptionGeneratorTool(test_mode=False)
registry._instances[NodeType.TOOL][ListingAgentTool.name] = ListingAgentTool(test_mode=False, upload=False)
print("Registry bootstrapped with live instances.")