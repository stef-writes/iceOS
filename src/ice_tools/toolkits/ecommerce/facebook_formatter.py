"""Facebook Marketplace payload formatter.

Transforms an *enriched product* dict produced by `listing_agent` into the JSON
structure expected by the Facebook Shops Product Catalog API.

This tool is *pure* – no IO – and therefore perfect to unit-test and reuse in
batch exporters.
"""
from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from ice_core.base_tool import ToolBase


class FacebookFormatterTool(ToolBase):
    """Convert enriched item → Facebook payload."""

    name: str = "facebook_formatter"
    description: str = "Format enriched product dict to Facebook Shops payload"

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute with context-first approach."""
        # Extract enriched_product from context
        enriched_product = kwargs.get("enriched_product")
        
        # If not found by that name, check for common alternatives
        if not enriched_product:
            for key in ["listing_agent", "product", "item"]:
                if key in kwargs and isinstance(kwargs[key], dict):
                    enriched_product = kwargs[key]
                    break
        
        if not enriched_product:
            raise ValueError("No product data found in context")
        
        partner_seller_id = kwargs.get("partner_seller_id", "Seller123")
        duplicate = enriched_product.get("duplicate", False)
        base = {
            "id": enriched_product.get("id", "auto-id"),
            "title": enriched_product.get("title", "Untitled"),
            "description": enriched_product.get("description", ""),
            "price": enriched_product.get("price", "0.00 USD"),
            "image_link": enriched_product.get("image", "https://example.com/placeholder.png"),
            "brand": enriched_product.get("brand", "Unknown"),
            "availability": "in stock",
            "condition": "new",
            "link": enriched_product.get("link", "https://example.com"),
            "partner_seller_id": partner_seller_id,
        }
        method = "UPDATE" if duplicate else "CREATE"
        return {"method": method, "data": base}
    
    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Accept any context - we'll extract what we need."""
        return {
            "type": "object",
            "additionalProperties": True,  # Accept all context
        }


# Factory function for creating FacebookFormatterTool instances
def create_facebook_formatter_tool() -> FacebookFormatterTool:
    """Create a FacebookFormatterTool instance."""
    return FacebookFormatterTool()

# Auto-registration -----------------------------------------------------------
from ice_core.unified_registry import register_tool_factory

register_tool_factory("facebook_formatter", "ice_tools.toolkits.ecommerce.facebook_formatter:create_facebook_formatter_tool")
