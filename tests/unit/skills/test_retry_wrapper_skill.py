import pytest

from ice_sdk.skills.system import SumSkill
from ice_sdk.skills.workflow.retry_wrapper_skill import RetryWrapperSkill


@pytest.mark.asyncio
async def test_retry_wrapper_skill(monkeypatch):
    calls = {"cnt": 0}

    async def flaky_execute(input_data):  # noqa: D401
        calls["cnt"] += 1
        if calls["cnt"] < 2:
            raise RuntimeError("flaky")
        return {"sum": 1}

    sum_skill = SumSkill()
    monkeypatch.setattr(sum_skill, "execute", flaky_execute)

    wrapped = RetryWrapperSkill(sum_skill, max_attempts=3, base_delay=0)
    res = await wrapped.execute({"numbers": [1]})
    assert res == {"sum": 1}
    assert calls["cnt"] == 2 