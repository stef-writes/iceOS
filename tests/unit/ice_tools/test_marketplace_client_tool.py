"""Unit tests for MarketplaceClientTool with httpx.MockTransport.

We keep the tests fully offline – no real network traffic.
"""
from __future__ import annotations

import asyncio
from typing import Dict

import pytest

import ice_tools.toolkits.ecommerce.marketplace_client  # noqa: F401 – side-effect registration
from ice_tools.toolkits.ecommerce.marketplace_client import MarketplaceClientTool


@pytest.mark.asyncio
async def test_marketplace_client_simulation_mode() -> None:
    """Simulation mode should bypass HTTP and return deterministic id."""
    tool = MarketplaceClientTool(test_mode=True)
    result = await tool.execute(item={"sku": "B2"})
    assert result["listing_id"] == "TEST-B2"

