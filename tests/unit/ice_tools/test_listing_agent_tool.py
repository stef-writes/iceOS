"""Unit test for ListingAgentTool (fully offline via test_mode)."""
from __future__ import annotations

import pytest

import ice_tools.toolkits.ecommerce.listing_agent  # noqa: F401 – side-effect registration
from ice_tools.toolkits.ecommerce.listing_agent import ListingAgentTool


@pytest.mark.asyncio
async def test_listing_agent_offline_happy_path() -> None:
    item = {"sku": "SKU1", "name": "Wonder Widget", "cost": 10.0}
    tool = ListingAgentTool(test_mode=True, margin_percent=20.0)
    result = await tool.execute(item=item)

    assert result["listing_id"].startswith("TEST-SKU1")
    assert result["price"] == 12.0  # 20% margin
    assert "Widget" in result["title"] or "Widget" in result["description"]
