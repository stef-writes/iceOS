from ice_sdk.skills import SkillBase


class testtool(SkillBase):
    name = "testtool"
    description = "A test resource"

    async def run(self, ctx, **kwargs):
        return {}
