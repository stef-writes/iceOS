"""Model Context Protocol (MCP) integration for tools."""
import asyncio
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .base import BaseTool, ToolContext


class MCPServer(BaseModel):
    """MCP server configuration."""
    command: str
    args: List[str]
    env: Dict[str, str] = {}
    working_dir: Optional[str] = None

class MCPServerStdio:
    """MCP server using stdio for communication."""
    def __init__(self, params: Dict[str, Any]):
        """Initialize MCP server.
        
        Args:
            params: Server parameters including command and args
        """
        self.server = MCPServer(**params)
        self.process: Optional[asyncio.subprocess.Process] = None
        self.tools: List[BaseTool] = []

    async def __aenter__(self):
        """Start the MCP server."""
        self.process = await asyncio.create_subprocess_exec(
            self.server.command,
            *self.server.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.server.env,
            cwd=self.server.working_dir
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop the MCP server."""
        if self.process:
            self.process.terminate()
            await self.process.wait()

    async def register_tool(self, tool: BaseTool):
        """Register a tool with the MCP server.
        
        Args:
            tool: Tool to register
        """
        if not self.process:
            raise RuntimeError("MCP server not started")

        # Static assurance for linters/mypy
        assert self.process is not None

        # Send tool registration message
        message = {
            "type": "register_tool",
            "tool": tool.as_dict()
        }
        await self._send_message(message)
        self.tools.append(tool)

    async def _send_message(self, message: Dict[str, Any]):
        """Send a message to the MCP server.
        
        Args:
            message: Message to send
        """
        if not self.process:
            raise RuntimeError("MCP server not started")

        # At this point ``self.process`` is guaranteed to be active.  Help *mypy* understand
        # that we are no longer dealing with an ``Optional``.
        assert self.process is not None

        # Send message
        message_str = json.dumps(message) + "\n"
        assert self.process.stdin is not None  # for static analysis
        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

        # Read response
        assert self.process.stdout is not None
        response = await self.process.stdout.readline()
        return json.loads(response.decode())

class MCPTool(BaseTool):
    """Base class for MCP tools."""
    def __init__(self, server: MCPServerStdio):
        """Initialize MCP tool.
        
        Args:
            server: MCP server instance
        """
        super().__init__()
        self.server = server

    async def run(self, ctx: ToolContext, **kwargs) -> Any:  # type: ignore[override]
        """Execute tool through MCP server.
        
        Args:
            ctx: Tool context
            **kwargs: Tool arguments
        """
        message = {
            "type": "execute_tool",
            "tool": self.name,
            "context": ctx.dict(),
            "args": kwargs
        }
        return await self.server._send_message(message) 