pytestmark = [__import__('pytest').mark.unit]

import pytest

from ice_sdk.tools.system.jinja_render_skill import JinjaRenderSkill
from ice_sdk.utils.errors import SkillExecutionError


@pytest.mark.asyncio
async def test_jinja_render_happy():
    """Jinja template with valid context should render expected output."""

    skill = JinjaRenderSkill()
    out = await skill.execute(template="Hello {{ name }}!", context={"name": "World"})

    assert out["rendered"] == "Hello World!"


@pytest.mark.asyncio
async def test_jinja_render_invalid_context():
    """Non-dict context should raise *SkillExecutionError*."""

    skill = JinjaRenderSkill()
    with pytest.raises(SkillExecutionError):
        await skill.execute(template="Hello", context="not a dict") 