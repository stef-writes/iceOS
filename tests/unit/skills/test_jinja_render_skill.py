import pytest

from ice_sdk.skills.system import JinjaRenderSkill


@pytest.mark.asyncio
async def test_jinja_render_basic():
    template = "Hello {name}"
    res = await JinjaRenderSkill().execute({"template": template, "context": {"name": "Alice"}})
    assert "Alice" in res["rendered"] 