pytestmark = [__import__('pytest').mark.unit]

import pytest

from ice_sdk.tools.system.jinja_render_tool import JinjaRenderTool
from ice_sdk.utils.errors import ToolExecutionError


@pytest.mark.asyncio
async def test_jinja_render_happy():
    """Jinja template with valid context should render expected output."""

    tool = JinjaRenderTool()
    out = await tool.execute(template="Hello {{ name }}!", context={"name": "World"})

    assert out["rendered"] == "Hello World!"


@pytest.mark.asyncio
async def test_jinja_render_invalid_context():
    """Non-dict context should raise *ToolExecutionError*."""

    tool = JinjaRenderTool()
    with pytest.raises(ToolExecutionError):
        await tool.execute(template="Hello", context="not a dict") 