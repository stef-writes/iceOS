"""Comprehensive tests for direct execution endpoints.

Tests the /v1/tools/{tool_name}, /v1/agents/{agent_name}, /v1/llm/{model} endpoints
with proper mocking and error handling scenarios.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.initialization import initialize_services
from ice_core.models.mcp import Blueprint, RunRequest, RunAck, RunResult
from ice_core.models import NodeType


# Initialize services before creating test client
initialize_services()
client = TestClient(app)


class TestDirectExecutionEndpoints:
    """Test direct execution endpoints with comprehensive scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_mocks(self, monkeypatch):
        """Setup mocks for MCP endpoints."""
        # Mock the start_run function
        async def mock_start_run(request: RunRequest) -> RunAck:
            return RunAck(
                run_id="test_run_123",
                status_endpoint="/api/v1/mcp/runs/test_run_123",
                events_endpoint="/api/v1/mcp/runs/test_run_123/events"
            )
        
        # Mock the get_result function
        async def mock_get_result(run_id: str) -> RunResult:
            from datetime import datetime
            return RunResult(
                run_id=run_id,
                success=True,
                output={"result": "test output"},
                error=None,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
        
        # Mock tool service
        mock_tool_service = Mock()
        mock_tool_service.available_tools.return_value = ["csv_reader", "web_search", "jinja_render"]
        
        # Patch the functions
        monkeypatch.setattr("ice_api.api.direct_execution.start_run", mock_start_run)
        monkeypatch.setattr("ice_api.api.direct_execution.get_result", mock_get_result)
        
        from ice_sdk.services.locator import ServiceLocator
        ServiceLocator.register("tool_service", mock_tool_service)
        
        yield
        
        # Cleanup
        ServiceLocator._services.clear()
    
    def test_execute_tool_success(self):
        """Test successful tool execution with wait_for_completion."""
        response = client.post("/v1/tools/csv_reader", json={
            "inputs": {"file_path": "/data/test.csv"},
            "options": {"delimiter": ","},
            "wait_for_completion": True,
            "timeout": 5.0
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run_123"
        assert data["status"] == "completed"
        assert data["output"] == {"result": "test output"}
        assert data["error"] is None
        assert data["telemetry_url"] == "/api/v1/mcp/runs/test_run_123/events"
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
    
    def test_execute_tool_not_found(self):
        """Test tool execution with non-existent tool."""
        response = client.post("/v1/tools/nonexistent_tool", json={
            "inputs": {},
            "wait_for_completion": True
        })
        
        assert response.status_code == 404
        assert "Tool 'nonexistent_tool' not found" in response.json()["detail"]
    
    def test_execute_tool_no_wait(self):
        """Test tool execution without waiting for completion."""
        response = client.post("/v1/tools/csv_reader", json={
            "inputs": {"file_path": "/data/test.csv"},
            "wait_for_completion": False
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run_123"
        assert data["status"] == "running"
        assert data["output"] is None
        assert data["error"] is None
    
    def test_execute_agent_success(self):
        """Test successful agent execution."""
        # Mock agent registry
        from ice_sdk.registry.agent import global_agent_registry
        global_agent_registry.register("test_agent", "tests.dummy.TestAgent")
        
        response = client.post("/v1/agents/test_agent", json={
            "inputs": {"task": "analyze data"},
            "options": {"max_iterations": 5},
            "wait_for_completion": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run_123"
        assert data["status"] == "completed"
        assert "suggestions" in data
    
    def test_execute_agent_not_found(self):
        """Test agent execution with non-existent agent."""
        response = client.post("/v1/agents/missing_agent", json={
            "inputs": {},
            "wait_for_completion": True
        })
        
        assert response.status_code == 404
        assert "Agent 'missing_agent' not found" in response.json()["detail"]
    
    def test_execute_llm_success(self):
        """Test successful LLM execution."""
        response = client.post("/v1/llm/gpt-4", json={
            "inputs": {"prompt": "Hello, world!"},
            "options": {
                "temperature": 0.8,
                "max_tokens": 100,
                "provider": "openai"
            },
            "wait_for_completion": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run_123"
        assert data["status"] == "completed"
        assert data["output"] == {"result": "test output"}
    
    def test_execute_llm_missing_prompt(self):
        """Test LLM execution without required prompt."""
        response = client.post("/v1/llm/gpt-4", json={
            "inputs": {},  # No prompt
            "wait_for_completion": True
        })
        
        assert response.status_code == 400
        assert "Prompt is required" in response.json()["detail"]
    
    def test_execute_llm_prompt_in_options(self):
        """Test LLM execution with prompt in options instead of inputs."""
        response = client.post("/v1/llm/gpt-4", json={
            "inputs": {},
            "options": {"prompt": "Hello from options!"},
            "wait_for_completion": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self, monkeypatch):
        """Test timeout handling for wait_for_completion."""
        # Mock get_result to always raise 202 (still running)
        from fastapi import HTTPException
        
        async def mock_get_result_running(run_id: str):
            raise HTTPException(status_code=202, detail="Still running")
        
        monkeypatch.setattr("ice_api.api.direct_execution.get_result", mock_get_result_running)
        
        # Use a very short timeout
        response = client.post("/v1/tools/csv_reader", json={
            "inputs": {"file_path": "/data/test.csv"},
            "wait_for_completion": True,
            "timeout": 0.1  # 100ms timeout
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "running"
        assert data["error"] == "Timeout waiting for completion"
    
    def test_execute_chain_success(self):
        """Test successful chain execution."""
        # Mock chain registry
        from ice_sdk.registry.chain import global_chain_registry
        global_chain_registry.register("test_chain", "tests.dummy.TestChain")
        
        response = client.post("/v1/chains/test_chain", json={
            "inputs": {"data": "test input"},
            "wait_for_completion": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_id"] == "test_run_123"
        assert data["status"] == "completed"
    
    def test_ai_suggestions_for_tools(self):
        """Test that AI suggestions are context-aware for different tools."""
        # Test CSV reader suggestions
        response = client.post("/v1/tools/csv_reader", json={
            "inputs": {"file_path": "/data/test.csv"},
            "wait_for_completion": True
        })
        
        suggestions = response.json()["suggestions"]
        assert any("validator" in s for s in suggestions)
        assert any("summarizer" in s for s in suggestions)
        
        # Test web search suggestions
        response = client.post("/v1/tools/web_search", json={
            "inputs": {"query": "test search"},
            "wait_for_completion": True
        })
        
        suggestions = response.json()["suggestions"]
        assert any("jinja" in s for s in suggestions)
        assert any("Summarize" in s for s in suggestions) 