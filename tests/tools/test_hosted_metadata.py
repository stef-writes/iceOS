from ice_sdk.tools.hosted import WebSearchTool, FileSearchTool


def test_hosted_tools_metadata():
    for tool_cls in (WebSearchTool, FileSearchTool):
        tool = tool_cls()
        assert tool.name
        assert tool.description
        assert tool.parameters_schema is not None 