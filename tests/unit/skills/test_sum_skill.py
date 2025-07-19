import pytest

from ice_sdk.skills.system import SumSkill


@pytest.mark.asyncio
async def test_sum_skill_basic():
    skill = SumSkill()
    res = await skill.execute({"numbers": [1, 2, 3.5]})
    assert res == {"sum": 6.5}


@pytest.mark.asyncio
async def test_sum_skill_input_coercion():
    res = await SumSkill().execute({"numbers": ["4", "1.5"]})
    assert res["sum"] == 5.5


@pytest.mark.asyncio
async def test_sum_skill_invalid_element():
    with pytest.raises(Exception):
        await SumSkill().execute({"numbers": [1, "x"]})
