"""ListingAgentTool – orchestrates pricing, copywriting, and marketplace upload.

Rebuilt with context-first design: accepts any context and intelligently
extracts what it needs rather than requiring specific parameter names.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from pydantic import Field, PositiveFloat

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

from .marketplace_client import MarketplaceClientTool
from .pricing_strategy import PricingStrategyTool
from .title_description_generator import TitleDescriptionGeneratorTool

__all__: list[str] = ["ListingAgentTool"]

logger = logging.getLogger(__name__)


class ListingAgentTool(ToolBase):
    """End-to-end listing: price → copy → marketplace upload.

    Context-first design: accepts any parameters and extracts what it needs.
    """

    # Metadata ----------------------------------------------------------------
    name: str = "listing_agent"
    description: str = "End-to-end listing: price → copy → marketplace upload."

    # Config fields -----------------------------------------------------------
    endpoint_url: str = Field(
        "https://example.com/api/listings", description="Marketplace endpoint"
    )
    api_key: str | None = Field(None, description="Marketplace Bearer token")
    margin_percent: PositiveFloat = Field(25.0, description="Pricing margin percent")
    model: str = Field("gpt-4o", description="LLM model for copy generation")
    test_mode: bool = False
    upload: bool = Field(True, description="Whether to upload listing to marketplace")

    _seen_skus: set[str] = set()

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute with context-first approach - accept any parameters."""

        # Extract item from context - could be direct or from loop
        item = self._extract_item(kwargs)

        # Normalize item data for consistent processing
        item = self._normalize_item(item)

        # Validate we have required fields
        self._validate_item(item)

        # 1. Price calculation
        pricing_tool = PricingStrategyTool(
            margin_percent=self.margin_percent,
            min_price=0.99,
            decimal_places=2,
        )
        price_out = await pricing_tool.execute(cost=float(item["cost"]))
        price = price_out["price"]

        # 2. Title & description generation
        title_tool = TitleDescriptionGeneratorTool(
            model=self.model,
            temperature=0.7,
            test_mode=self.test_mode,
        )
        copy_out = await title_tool.execute(item=item)
        title = copy_out["title"]
        description = copy_out["description"]

        # 3. Marketplace upload (optional)
        payload: Dict[str, Any] = {
            **item,
            "title": title,
            "description": description,
            "price": price,
        }

        if self.upload:
            market_tool = MarketplaceClientTool(
                endpoint_url=self.endpoint_url,
                api_key=self.api_key,  # type: ignore[arg-type]
                test_mode=self.test_mode,
            )
            market_out = await market_tool.execute(item=payload)
            listing_id = market_out["listing_id"]
        else:
            # Generate deterministic local ID
            listing_id = f"LOC-{item.get('sku', 'item')}"

        # Duplicate tracking
        duplicate = self._check_duplicate(item["sku"])

        return {
            "listing_id": listing_id,
            "title": title,
            "description": description,
            "price": price,
            "duplicate": duplicate,
        }

    def _extract_item(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract item from various context structures."""

        # Direct item parameter
        if "item" in context:
            return context["item"]

        # Loop variable with different names
        for key in ["product", "row", "record"]:
            if key in context and isinstance(context[key], dict):
                return context[key]

        # If context itself looks like an item
        if "Product/Item" in context or "name" in context:
            return context

        # Check nested structures
        for key, value in context.items():
            if isinstance(value, dict) and ("Product/Item" in value or "name" in value):
                return value

        raise ValidationError(
            "Could not find item data in context. Expected 'item' parameter or "
            "item-like structure with 'name' or 'Product/Item' field."
        )

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize various item formats to consistent structure."""

        # Map common CSV column names
        key_map = {
            "Product Code/SKU": "sku",
            "Product/Item": "name",
            "Suggested Price": "cost",
            "Cost": "cost",
        }

        normalized: Dict[str, Any] = {}
        for k, v in item.items():
            if k in key_map:
                normalized[key_map[k]] = v
            else:
                normalized[k] = v

        # Clean up cost field
        if isinstance(normalized.get("cost"), str):
            import re

            match = re.search(r"([0-9]+(?:\.[0-9]+)?)", normalized["cost"])
            if match:
                normalized["cost"] = float(match.group(1))
            else:
                # If no number found, try to extract any numeric value
                import re

                numbers = re.findall(r"([0-9]+(?:\.[0-9]+)?)", normalized["cost"])
                if numbers:
                    normalized["cost"] = float(numbers[0])
                else:
                    # Default to minimum cost if no number found
                    normalized["cost"] = 1.0

        # Auto-generate SKU if missing
        if "sku" not in normalized:
            import hashlib
            import re

            base_name = str(normalized.get("name", "item"))
            slug = re.sub(r"[^A-Za-z0-9]+", "-", base_name).strip("-").lower()
            sku_hash = hashlib.sha1(base_name.encode()).hexdigest()[:6]
            normalized["sku"] = f"{slug}-{sku_hash}"[:30]

        return normalized

    def _validate_item(self, item: Dict[str, Any]) -> None:
        """Validate item has required fields."""
        required_fields = {"name", "cost"}
        missing = required_fields - set(item.keys())
        if missing:
            raise ValidationError(
                f"Item missing required fields: {sorted(missing)}. "
                f"Available fields: {sorted(item.keys())}"
            )

    def _check_duplicate(self, sku: str) -> bool:
        """Check if SKU has been seen before."""
        if sku in self._seen_skus:
            return True
        self._seen_skus.add(sku)
        return False

    # ------------------------------------------------------------------
    # Schema overrides for context-first approach
    # ------------------------------------------------------------------

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Accept any context - we'll extract what we need."""
        return {
            "type": "object",
            "additionalProperties": True,  # Accept all context
        }

    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Output schema for the listing result."""
        return {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "price": {"type": "number"},
                "duplicate": {"type": "boolean"},
            },
            "required": ["listing_id", "title", "description", "price"],
            "additionalProperties": False,
        }


# Factory function for creating ListingAgentTool instances
def create_listing_agent_tool(
    test_mode: bool = False, 
    upload: bool = True, 
    margin_percent: float = 25.0,
    model: str = "gpt-4o",
    endpoint_url: str = "https://example.com/api/listings",
    api_key: str | None = None
) -> ListingAgentTool:
    """Create a ListingAgentTool with the specified configuration."""
    return ListingAgentTool(
        test_mode=test_mode,
        upload=upload,
        margin_percent=margin_percent,
        model=model,
        endpoint_url=endpoint_url,
        api_key=api_key
    )

# Auto-registration -----------------------------------------------------------
from ice_core.unified_registry import register_tool_factory

register_tool_factory("listing_agent", "ice_tools.toolkits.ecommerce.listing_agent:create_listing_agent_tool")
