"""Initialization module for FB Marketplace Seller demo components.

This module is automatically loaded by the iceOS server to register
all tools, agents, and workflows for the FB Marketplace Seller use case.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from ice_core.unified_registry import registry
from ice_core.models.enums import NodeType

logger = logging.getLogger(__name__)


def initialize_all(mode: str = "mcp") -> bool:
    """Initialize all FB Marketplace Seller components.
    
    Args:
        mode: Initialization mode ("mcp" for server, "debug" for manual testing)
        
    Returns:
        True if initialization succeeded, False otherwise
    """
    try:
        logger.info("Initializing FB Marketplace Seller components...")
        
        # Register tools
        _register_tools()
        
        # In the future, we could also register:
        # _register_agents()
        # _register_workflows()
        
        logger.info("✅ FB Marketplace Seller initialization complete")
        return True
        
    except Exception as e:
        logger.error(f"❌ FB Marketplace Seller initialization failed: {e}")
        return False


def _register_tools() -> None:
    """Register all FB Marketplace Seller tools."""
    from .tools.read_inventory_csv import ReadInventoryCSVTool
    from .tools.dedupe_items import DedupeItemsTool
    from .tools.ai_enrichment import AIEnrichmentTool
    from .tools.facebook_publisher import FacebookPublisherTool
    
    tools = [
        ReadInventoryCSVTool(),
        DedupeItemsTool(), 
        AIEnrichmentTool(),
        FacebookPublisherTool(),
    ]
    
    for tool in tools:
        registry.register_instance(NodeType.TOOL, tool.name, tool)
        logger.info(f"✅ Registered tool: {tool.name}")


def get_available_tools() -> Dict[str, Any]:
    """Return metadata about available FB Marketplace tools."""
    return {
        "read_inventory_csv": {
            "description": "Read and validate CSV inventory files",
            "category": "data",
            "inputs": {"csv_file": "string"},
            "outputs": {"success": "boolean", "items_imported": "integer", "clean_items": "array"}
        },
        "dedupe_items": {
            "description": "Remove duplicate inventory items", 
            "category": "data",
            "inputs": {"items": "array"},
            "outputs": {"unique_items": "array", "duplicates_removed": "integer"}
        },
        "ai_enrichment": {
            "description": "Enhance product descriptions with AI",
            "category": "ai",
            "inputs": {"items": "array"},
            "outputs": {"enriched_items": "array"}
        },
        "facebook_publisher": {
            "description": "Publish items to Facebook Marketplace",
            "category": "social",
            "inputs": {"items": "array"},
            "outputs": {"published_count": "integer", "failed_items": "array"}
        }
    } 