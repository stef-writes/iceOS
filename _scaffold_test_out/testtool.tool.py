from ice_sdk.tools.base import BaseTool


class testtool(BaseTool):
    name = "testtool"
    description = "A test resource"

    async def run(self, ctx, **kwargs):
        return {}
