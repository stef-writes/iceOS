"""Unit tests for TitleDescriptionGeneratorTool (offline test_mode)."""
from __future__ import annotations

import pytest

import ice_tools.title_description_generator  # noqa: F401 – side-effect registration
from ice_tools.title_description_generator import TitleDescriptionGeneratorTool


@pytest.mark.asyncio
async def test_title_description_generator_test_mode() -> None:
    tool = TitleDescriptionGeneratorTool(test_mode=True)
    item = {"sku": "X1", "name": "Magic Widget"}
    result = await tool.execute(item=item)
    assert result["title"].startswith("TEST Magic Widget")
    assert "Widget" in result["description"]
