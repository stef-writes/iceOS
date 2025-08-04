"""ListingAgentTool – orchestrates pricing, copywriting, and marketplace upload.

Uses the other tools from the same toolkit; still itself a *Tool* so that it
can slot into workflows like any atomic operation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from pydantic import Field, PositiveFloat

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

from .pricing_strategy import PricingStrategyTool
from .title_description_generator import TitleDescriptionGeneratorTool
from .marketplace_client import MarketplaceClientTool

__all__: list[str] = ["ListingAgentTool"]

logger = logging.getLogger(__name__)


class ListingAgentTool(ToolBase):
    """End-to-end listing: price → copy → marketplace upload."""

    # Metadata ----------------------------------------------------------------

    # Pre-declare output schema for discovery
    output_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "listing_id": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "price": {"type": "number"},
        },
        "required": ["listing_id", "title", "description", "price"],
        "additionalProperties": False,
    }
    name: str = "listing_agent"
    description: str = "End-to-end listing: price → copy → marketplace upload."

    # Config fields -----------------------------------------------------------
    endpoint_url: str = Field("https://example.com/api/listings", description="Marketplace endpoint")
    api_key: str | None = Field(None, description="Marketplace Bearer token")
    margin_percent: PositiveFloat = Field(25.0, description="Pricing margin percent")
    model: str = Field("gpt-4o", description="LLM model for copy generation")
    test_mode: bool = False

    async def _execute_impl(self, *, item: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        required_fields = {"sku", "name", "cost"}
        if not required_fields.issubset(item):
            raise ValidationError(f"'item' must include {sorted(required_fields)}")

        # 1. Price calculation -------------------------------------------------
        pricing_tool = PricingStrategyTool(
            margin_percent=self.margin_percent,
            min_price=0.99,
            decimal_places=2,
        )
        price_out = await pricing_tool.execute(cost=float(item["cost"]))
        price = price_out["price"]

        # 2. Title & description generation -----------------------------------
        title_tool = TitleDescriptionGeneratorTool(
            model=self.model,
            temperature=0.7,
            test_mode=self.test_mode,
        )
        copy_out = await title_tool.execute(item=item)
        title = copy_out["title"]
        description = copy_out["description"]

        # 3. Marketplace upload ------------------------------------------------
        payload: Dict[str, Any] = {
            **item,
            "title": title,
            "description": description,
            "price": price,
        }
        market_tool = MarketplaceClientTool(
            endpoint_url=self.endpoint_url,
            api_key=self.api_key,  # type: ignore[arg-type]
            test_mode=self.test_mode,
        )
        market_out = await market_tool.execute(item=payload)
        listing_id = market_out["listing_id"]

        return {
            "listing_id": listing_id,
            "title": title,
            "description": description,
            "price": price,
        }

    # ------------------------------------------------------------------
    # Schema overrides --------------------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:  # noqa: D401 – override
        """JSON Schema describing the tool's output."""
        return {
            "type": "object",
            "properties": {
                "listing_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "price": {"type": "number"},
            },
            "required": ["listing_id", "title", "description", "price"],
            "additionalProperties": False,
        }


# Auto-registration -----------------------------------------------------------
_instance = ListingAgentTool(test_mode=True)
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
