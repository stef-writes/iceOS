"""Unit tests for PricingStrategyTool."""
from __future__ import annotations

import pytest

from ice_tools.ecommerce.pricing_strategy import PricingStrategyTool


@pytest.mark.asyncio
async def test_pricing_strategy_default_margin() -> None:
    tool = PricingStrategyTool(margin_percent=20.0, min_price=1.0, decimal_places=2)
    result = await tool.execute(cost=10.0)
    # 20% margin → 12.0
    assert result["price"] == 12.0


@pytest.mark.asyncio
async def test_pricing_strategy_min_price_applied() -> None:
    tool = PricingStrategyTool(margin_percent=5.0, min_price=15.0, decimal_places=2)
    result = await tool.execute(cost=10.0)
    # 5% margin on 10 → 10.5 but min_price=15 so expect 15.0
    assert result["price"] == 15.0


@pytest.mark.asyncio
async def test_pricing_strategy_rounding() -> None:
    tool = PricingStrategyTool(margin_percent=33.333, min_price=1.0, decimal_places=2)
    result = await tool.execute(cost=7.77)
    # (7.77 * 1.33333…) = 10.3599… → 10.36 after rounding
    assert result["price"] == 10.36
