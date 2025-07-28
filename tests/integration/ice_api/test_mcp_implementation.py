"""Comprehensive test suite for MCP (Model Context Protocol) implementation.

Tests all MCP functionality including:
- Protocol compliance (JSON-RPC 2.0)
- Initialization and capability negotiation  
- Tool discovery and execution
- Resource listing and reading
- Prompt listing and generation
- Error handling and edge cases
- Session management
- Integration with iceOS components
"""

import json
import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

from ice_api.main import app
from ice_api.api.mcp_jsonrpc import (
    mcp_session, 
    handle_initialize,
    handle_tools_list,
    handle_tools_call,
    handle_resources_list,
    handle_resources_read,
    handle_prompts_list,
    handle_prompts_get,
    MCPRequest,
    MCPResponse,
    MCPError
)


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and JSON-RPC 2.0 spec."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Async HTTP client for testing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    def test_mcp_request_validation(self):
        """Test MCP request model validation."""
        # Valid request
        valid_request = MCPRequest(
            method="initialize",
            params={"protocolVersion": "2024-11-05"},
            id="test-1"
        )
        assert valid_request.jsonrpc == "2.0"
        assert valid_request.method == "initialize"

        # Invalid JSON-RPC version
        with pytest.raises(ValueError):
            MCPRequest(jsonrpc="1.0", method="test")

    def test_mcp_response_validation(self):
        """Test MCP response model validation."""
        # Valid response with result
        response = MCPResponse(id="test-1", result={"success": True})
        assert response.jsonrpc == "2.0"
        assert response.error is None

        # Valid response with error
        error_response = MCPResponse(
            id="test-1", 
            error=MCPError(code=-32000, message="Test error")
        )
        assert error_response.result is None

        # Invalid - both result and error
        with pytest.raises(ValueError):
            MCPResponse(
                id="test-1",
                result={"test": True},
                error=MCPError(code=-32000, message="error")
            )

    @pytest.mark.asyncio
    async def test_json_rpc_endpoint(self, async_client):
        """Test JSON-RPC endpoint with valid requests."""
        # Test initialize
        initialize_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            },
            "id": 1
        }

        response = await async_client.post("/mcp/", json=initialize_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data
        assert data["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in data["result"]
        assert "serverInfo" in data["result"]

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self, async_client):
        """Test handling of malformed JSON requests."""
        response = await async_client.post(
            "/mcp/", 
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32700  # Parse error

    @pytest.mark.asyncio
    async def test_invalid_method_handling(self, async_client):
        """Test handling of invalid/unknown methods."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "id": 1
        }

        response = await async_client.post("/mcp/", json=request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found


class TestMCPInitialization:
    """Test MCP initialization and session management."""

    def setup_method(self):
        """Reset session state before each test."""
        mcp_session.reset()

    @pytest.mark.asyncio
    async def test_initialization_success(self):
        """Test successful MCP initialization."""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }

        result = await handle_initialize(params)

        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert result["capabilities"]["tools"]["listChanged"] is True
        assert result["capabilities"]["resources"]["subscribe"] is True
        assert result["serverInfo"]["name"] == "iceOS"
        
        # Check session state
        assert mcp_session.initialized is True
        assert mcp_session.protocol_version == "2024-11-05"

    @pytest.mark.asyncio
    async def test_initialization_with_different_version(self):
        """Test initialization with different protocol version."""
        params = {
            "protocolVersion": "2024-10-01",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }

        result = await handle_initialize(params)
        
        # Should still work but use client version
        assert result["protocolVersion"] == "2024-10-01"
        assert mcp_session.protocol_version == "2024-10-01"

    @pytest.mark.asyncio
    async def test_uninitialized_session_protection(self, async_client):
        """Test that non-initialize methods require initialization."""
        mcp_session.reset()  # Ensure not initialized

        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }

        response = await async_client.post("/mcp/", json=request)
        data = response.json()
        
        assert "error" in data
        assert data["error"]["code"] == -32002  # Server not initialized


class TestMCPToolsInterface:
    """Test MCP tools interface functionality."""

    def setup_method(self):
        """Initialize session for tools testing."""
        mcp_session.reset()
        mcp_session.initialized = True

    @pytest.mark.asyncio
    async def test_tools_list_success(self):
        """Test successful tools listing."""
        with patch('ice_api.api.mcp_jsonrpc.get_tool_service') as mock_tool_service:
            mock_service = Mock()
            mock_service.available_tools.return_value = ["csv_processor", "http_client"]
            mock_service.get_tool_class.return_value = Mock(description="Test tool")
            mock_tool_service.return_value = mock_service

            with patch('ice_api.api.mcp_jsonrpc.global_agent_registry') as mock_agent_registry:
                mock_agent_registry.available.return_value = ["market_intelligence"]

                with patch('ice_api.api.mcp_jsonrpc.registry') as mock_registry:
                    mock_registry.available_instances.return_value = [("document_assistant", Mock())]

                    result = await handle_tools_list()

                    assert "tools" in result
                    tools = result["tools"]
                    
                    # Should have tools, agents, and workflows
                    tool_names = [tool["name"] for tool in tools]
                    assert "tool:csv_processor" in tool_names
                    assert "agent:market_intelligence" in tool_names
                    assert "workflow:document_assistant" in tool_names
                    
                    # Check tool schema
                    csv_tool = next(t for t in tools if t["name"] == "tool:csv_processor")
                    assert "inputSchema" in csv_tool
                    assert csv_tool["inputSchema"]["type"] == "object"
                    assert "inputs" in csv_tool["inputSchema"]["properties"]

    @pytest.mark.asyncio
    async def test_tools_list_with_failures(self):
        """Test tools listing with some component failures."""
        with patch('ice_api.api.mcp_jsonrpc.get_tool_service') as mock_tool_service:
            # Tool service fails
            mock_tool_service.side_effect = Exception("Tool service error")

            with patch('ice_api.api.mcp_jsonrpc.global_agent_registry') as mock_agent_registry:
                mock_agent_registry.available.return_value = ["test_agent"]

                result = await handle_tools_list()
                
                # Should still return agents even if tools fail
                assert "tools" in result
                tool_names = [tool["name"] for tool in result["tools"]]
                assert "agent:test_agent" in tool_names

    @pytest.mark.asyncio
    async def test_tool_execution_success(self):
        """Test successful tool execution."""
        params = {
            "name": "tool:csv_processor",
            "arguments": {
                "inputs": {"file_path": "test.csv"},
                "options": {"timeout": 30}
            }
        }

        with patch('ice_api.api.mcp_jsonrpc.validate_tool_exists') as mock_validate:
            mock_validate.return_value = None  # Tool exists

            with patch('ice_api.api.mcp_jsonrpc.start_run') as mock_start_run:
                mock_run_ack = Mock()
                mock_run_ack.run_id = "test-run-123"
                mock_start_run.return_value = mock_run_ack

                with patch('ice_api.api.mcp_jsonrpc.wait_for_completion') as mock_wait:
                    mock_wait.return_value = {
                        "status": "completed",
                        "output": {"result": "processed"},
                        "error": None
                    }

                    result = await handle_tools_call(params)

                    assert "content" in result
                    assert len(result["content"]) == 1
                    assert result["content"][0]["type"] == "text"
                    
                    # Parse the JSON result
                    output = json.loads(result["content"][0]["text"])
                    assert output["result"] == "processed"

    @pytest.mark.asyncio
    async def test_tool_execution_invalid_name(self):
        """Test tool execution with invalid name format."""
        params = {
            "name": "invalid_name_format",  # Missing type prefix
            "arguments": {}
        }

        with pytest.raises(ValueError, match="Invalid tool name format"):
            await handle_tools_call(params)

    @pytest.mark.asyncio
    async def test_tool_execution_nonexistent_tool(self):
        """Test tool execution with nonexistent tool."""
        params = {
            "name": "tool:nonexistent",
            "arguments": {}
        }

        with patch('ice_api.api.mcp_jsonrpc.get_tool_service') as mock_tool_service:
            mock_service = Mock()
            mock_service.available_tools.return_value = []
            mock_tool_service.return_value = mock_service

            with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
                await handle_tools_call(params)

    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self):
        """Test tool execution timeout handling."""
        params = {
            "name": "tool:slow_tool",
            "arguments": {"timeout": 1.0}  # Short timeout
        }

        with patch('ice_api.api.mcp_jsonrpc.validate_tool_exists'):
            with patch('ice_api.api.mcp_jsonrpc.start_run') as mock_start_run:
                mock_run_ack = Mock()
                mock_run_ack.run_id = "test-run-timeout"
                mock_start_run.return_value = mock_run_ack

                with patch('ice_api.api.mcp_jsonrpc.wait_for_completion') as mock_wait:
                    mock_wait.return_value = {
                        "status": "timeout",
                        "output": None,
                        "error": "Execution timeout after 1.0 seconds"
                    }

                    with pytest.raises(ValueError, match="Tool execution timed out"):
                        await handle_tools_call(params)


class TestMCPResourcesInterface:
    """Test MCP resources interface functionality."""

    def setup_method(self):
        """Initialize session for resources testing."""
        mcp_session.reset()
        mcp_session.initialized = True

    @pytest.mark.asyncio
    async def test_resources_list_success(self):
        """Test successful resources listing."""
        result = await handle_resources_list()

        assert "resources" in result
        resources = result["resources"]
        
        # Check expected resources
        resource_uris = [r["uri"] for r in resources]
        assert "iceos://templates/bci_investment_lab" in resource_uris
        assert "iceos://templates/document_assistant" in resource_uris
        assert "iceos://docs/architecture" in resource_uris

        # Check resource structure
        template_resource = next(r for r in resources if "templates" in r["uri"])
        assert "name" in template_resource
        assert "description" in template_resource
        assert template_resource["mimeType"] == "application/json"

    @pytest.mark.asyncio
    async def test_resource_read_template(self):
        """Test reading a template resource."""
        params = {"uri": "iceos://templates/bci_investment_lab"}

        with patch('ice_api.api.mcp_jsonrpc.get_template_blueprint') as mock_get_template:
            mock_template = {
                "template": "bci_investment_lab",
                "description": "Test template",
                "nodes": []
            }
            mock_get_template.return_value = mock_template

            result = await handle_resources_read(params)

            assert "contents" in result
            assert len(result["contents"]) == 1
            
            content = result["contents"][0]
            assert content["uri"] == params["uri"]
            assert content["mimeType"] == "application/json"
            
            # Parse and verify JSON content
            template_data = json.loads(content["text"])
            assert template_data["template"] == "bci_investment_lab"

    @pytest.mark.asyncio
    async def test_resource_read_documentation(self):
        """Test reading a documentation resource."""
        params = {"uri": "iceos://docs/architecture"}

        with patch('ice_api.api.mcp_jsonrpc.get_documentation') as mock_get_docs:
            mock_docs = "# Architecture\nTest documentation content"
            mock_get_docs.return_value = mock_docs

            result = await handle_resources_read(params)

            assert "contents" in result
            content = result["contents"][0]
            assert content["mimeType"] == "text/markdown"
            assert "Architecture" in content["text"]

    @pytest.mark.asyncio
    async def test_resource_read_invalid_uri(self):
        """Test reading resource with invalid URI."""
        params = {"uri": "invalid://unknown/resource"}

        with pytest.raises(ValueError, match="Unknown resource URI"):
            await handle_resources_read(params)


class TestMCPPromptsInterface:
    """Test MCP prompts interface functionality."""

    def setup_method(self):
        """Initialize session for prompts testing."""
        mcp_session.reset()
        mcp_session.initialized = True

    @pytest.mark.asyncio
    async def test_prompts_list_success(self):
        """Test successful prompts listing."""
        result = await handle_prompts_list()

        assert "prompts" in result
        prompts = result["prompts"]
        
        # Check expected prompts
        prompt_names = [p["name"] for p in prompts]
        assert "create_investment_analysis" in prompt_names
        assert "setup_document_qa" in prompt_names
        assert "automate_marketplace_selling" in prompt_names

        # Check prompt structure
        investment_prompt = next(p for p in prompts if p["name"] == "create_investment_analysis")
        assert "description" in investment_prompt
        assert "arguments" in investment_prompt
        assert len(investment_prompt["arguments"]) > 0
        
        # Check argument structure
        sector_arg = next(a for a in investment_prompt["arguments"] if a["name"] == "sector")
        assert sector_arg["required"] is True

    @pytest.mark.asyncio
    async def test_prompt_get_investment_analysis(self):
        """Test getting investment analysis prompt."""
        params = {
            "name": "create_investment_analysis",
            "arguments": {
                "sector": "AI/ML",
                "timeframe": "quarterly"
            }
        }

        result = await handle_prompts_get(params)

        assert "description" in result
        assert "messages" in result
        assert len(result["messages"]) == 1
        
        message = result["messages"][0]
        assert message["role"] == "user"
        assert "content" in message
        assert "AI/ML" in message["content"]["text"]
        assert "quarterly" in message["content"]["text"]

    @pytest.mark.asyncio
    async def test_prompt_get_unknown_prompt(self):
        """Test getting unknown prompt."""
        params = {
            "name": "unknown_prompt",
            "arguments": {}
        }

        with pytest.raises(ValueError, match="Unknown prompt"):
            await handle_prompts_get(params)


class TestMCPErrorHandling:
    """Test comprehensive error handling scenarios."""

    def setup_method(self):
        """Initialize session for error testing."""
        mcp_session.reset()
        mcp_session.initialized = True

    @pytest.mark.asyncio
    async def test_notification_handling(self, async_client):
        """Test MCP notification handling (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": "initialized"
            # No ID = notification
        }

        response = await async_client.post("/mcp/", json=notification)
        
        # Notifications return empty response
        assert response.status_code == 200
        data = response.json()
        assert data == {}

    @pytest.mark.asyncio
    async def test_ping_handling(self, async_client):
        """Test ping method handling."""
        mcp_session.initialized = True
        
        request = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1
        }

        response = await async_client.post("/mcp/", json=request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["result"] == {}

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client):
        """Test handling of concurrent MCP requests."""
        mcp_session.initialized = True
        
        requests = [
            {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": i
            }
            for i in range(5)
        ]

        # Send multiple concurrent requests
        tasks = [
            async_client.post("/mcp/", json=req)
            for req in requests
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for i, response in enumerate(responses):
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == i
            assert "result" in data


class TestMCPIntegration:
    """Test MCP integration with iceOS components."""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_execution(self, async_client):
        """Test complete end-to-end workflow execution via MCP."""
        # Initialize session
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "integration-test", "version": "1.0"}
            },
            "id": "init"
        }

        init_response = await async_client.post("/mcp/", json=init_request)
        assert init_response.status_code == 200

        # List tools
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": "list"
        }

        list_response = await async_client.post("/mcp/", json=list_request)
        assert list_response.status_code == 200
        
        tools_data = list_response.json()
        assert "result" in tools_data
        assert "tools" in tools_data["result"]

    @pytest.mark.asyncio
    async def test_mcp_stdio_server_initialization(self):
        """Test stdio MCP server can initialize properly."""
        from ice_api.mcp_stdio_server import StdioMCPServer
        
        server = StdioMCPServer()
        assert server.initialized is False
        
        # Test request handling
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1
        }
        
        response = await server.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert server.initialized is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 