import pytest
from httpx import AsyncClient

from ice_sdk.tools.web.chat_ui_deployment import ChatUIDeploymentTool, ToolContext
from tests.stubs.chat_ui_service import app as stub_app


@pytest.mark.asyncio
async def test_chat_ui_deployment_tool_live(monkeypatch):
    """ChatUIDeploymentTool should hit live endpoint and return snippet."""

    tool = ChatUIDeploymentTool()

    # Patch httpx.AsyncClient **before** invoking the tool so its internal use
    # routes requests to the in-process FastAPI app.
    import ice_sdk.tools.web.chat_ui_deployment as cud

    def _client_factory(*args, **kwargs):  # noqa: WPS430 – test helper
        # Always return a fresh client bound to the stub app so context
        # managers work as expected.
        return AsyncClient(app=stub_app, base_url="http://testserver")

    monkeypatch.setattr(cud.httpx, "AsyncClient", _client_factory, raising=False)

    result = await tool.run(
        ctx=ToolContext(agent_id="demo", session_id="sess-123"),
        endpoint="http://testserver/chatbots",
        api_key="dummy-key",
        config={
            "system_prompt": "You are helpful",
            "examples": [],
        },
    )

    assert result["embed_script"].startswith("<script src='http://testserver/embed/")
