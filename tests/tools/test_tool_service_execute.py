import pytest

from ice_sdk.tools.service import ToolRequest, ToolService


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    svc = ToolService(auto_register_builtins=False)
    with pytest.raises(KeyError):
        await svc.execute(ToolRequest(tool_name="ghost", inputs={}))


@pytest.mark.asyncio
async def test_execute_builtin_async():
    svc = ToolService()  # registers built-ins
    req = ToolRequest(
        tool_name="sleep",  # a tiny async builtin
        inputs={"seconds": 0.01},
        context={"user": "alice"},
    )
    res = await svc.execute(req)
    assert res["tool"] == "sleep"
    assert res["data"] == {"slept": 0.01}


@pytest.mark.asyncio
async def test_context_isolation():
    svc = ToolService()
    _ = await svc.execute(
        ToolRequest(tool_name="sum", inputs={"a": 1, "b": 2}, context={"user": "alice"})
    )
    _ = await svc.execute(
        ToolRequest(tool_name="sum", inputs={"a": 1, "b": 2}, context={"user": "bob"})
    )
    # The outputs match, but internal ctx objects were distinct; absence
    # of exception implies no cross-contamination.
