# ruff: noqa: E402
from __future__ import annotations

"""ice_sdk.tools – public façade for all tool-related APIs."""


from .base import BaseTool, ToolContext, ToolError, function_tool
from .hosted import ComputerTool, FileSearchTool, WebSearchTool
from .mcp_tool import MCPTool  # Generic Model Context Protocol tool

# Built-ins sub-package -------------------------------------------------------

__all__: list[str] = [
    # Core abstractions
    "BaseTool",
    "ToolContext",
    "ToolError",
    "function_tool",
    # Hosted tools
    "WebSearchTool",
    "FileSearchTool",
    "ComputerTool",
    "MCPTool",
]
