import pytest

from ice_sdk.skills.db import IndexAdvisorSkill


@pytest.mark.asyncio
async def test_index_advisor_skill():
    skill = IndexAdvisorSkill()
    res = await skill.execute({"table": "users", "query_samples": ["SELECT * FROM users WHERE email='a'", "select id from users"]})
    assert "suggestions" in res
    assert isinstance(res["suggestions"], list) 