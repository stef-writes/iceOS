import asyncio
import pytest

from ice_sdk.skills.system import SleepSkill


@pytest.mark.asyncio
async def test_sleep_skill_zero(monkeypatch):
    start = asyncio.get_event_loop().time()
    res = await SleepSkill().execute({"seconds": 0})
    elapsed = asyncio.get_event_loop().time() - start
    assert res == {"slept": 0}
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_sleep_skill_bounds():
    skill = SleepSkill()
    with pytest.raises(Exception):
        await skill.execute({"seconds": -1})
    with pytest.raises(Exception):
        await skill.execute({"seconds": 61}) 