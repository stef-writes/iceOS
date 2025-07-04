import pytest

from ice_sdk.tools.builtins.essay_tools import (
    KeywordDensityTool,
    LanguageStyleAdapterTool,
)


@pytest.mark.asyncio
async def test_language_style_adapter_academic():
    tool = LanguageStyleAdapterTool()
    result = await tool.run(text="AI can't be ignored.", style="academic")
    assert "styled_text" in result
    assert "cannot" in result["styled_text"]


@pytest.mark.asyncio
async def test_keyword_density():
    tool = KeywordDensityTool()
    text = "AI helps. AI learns. We use AI."
    result = await tool.run(text=text, keywords=["AI", "learns"])
    assert result["total_words"] > 0
    assert "AI" in result["density"]
    # Density for AI should be > 0
    assert result["density"]["AI"] > 0
