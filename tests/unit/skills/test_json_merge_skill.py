import asyncio

import pytest

from ice_sdk.skills.system import JSONMergeSkill


@pytest.mark.asyncio
async def test_json_merge_skill():
    skill = JSONMergeSkill()
    docs = [{"a": 1, "b": {"x": 1}}, {"b": {"y": 2}}]
    res = await skill.execute({"docs": docs})
    assert res == {"merged": {"a": 1, "b": {"x": 1, "y": 2}}} 