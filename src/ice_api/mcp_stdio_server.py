#!/usr/bin/env python3
"""MCP stdio transport server for iceOS.

This allows iceOS to be used as an MCP server via stdio transport,
which is the most common way MCP servers are integrated with clients.

Usage:
    python -m ice_api.mcp_stdio_server

Or from command line:
    python src/ice_api/mcp_stdio_server.py
"""

import asyncio
import json
import sys
from typing import Any, Dict

from ice_api.api.mcp_jsonrpc import (
    handle_components_validate,
    handle_initialize,
    handle_prompts_get,
    handle_prompts_list,
    handle_resources_list,
    handle_resources_read,
    handle_tools_call,
    handle_tools_list,
)


class StdioMCPServer:
    """MCP server using stdio transport."""
    
    def __init__(self) -> None:
        self.initialized = False
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single MCP JSON-RPC request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            # Route to appropriate handler
            if method == "initialize":
                result = await handle_initialize(params)
                self.initialized = True
            elif method == "tools/list":
                result = await handle_tools_list()
            elif method == "tools/call":
                result = await handle_tools_call(params)
            elif method == "resources/list":
                result = await handle_resources_list()
            elif method == "resources/read":
                result = await handle_resources_read(params)
            elif method == "prompts/list":
                result = await handle_prompts_list()
            elif method == "prompts/get":
                result = await handle_prompts_get(params)
            elif method == "components/validate":
                result = await handle_components_validate(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0", 
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    async def run(self) -> None:
        """Main server loop reading from stdin and writing to stdout."""
        while True:
            try:
                # Read a line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    # Send error response
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {e}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
                    continue
                
                # Handle request
                response = await self.handle_request(request)
                
                # Send response
                print(json.dumps(response), flush=True)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Send error response
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32000,
                        "message": f"Server error: {e}"
                    }
                }
                print(json.dumps(error_response), flush=True)


async def main() -> None:
    """Main entry point for stdio MCP server."""
    # Initialize logging to stderr so it doesn't interfere with JSON-RPC
    import logging
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize iceOS services
    try:
        import importlib

        # Dynamic import to avoid direct layer dependency
        initialize_orchestrator = importlib.import_module("ice_orchestrator").initialize_orchestrator
        initialize_orchestrator()
    except Exception as e:
        print(f"Failed to initialize iceOS: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Start MCP server
    server = StdioMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 