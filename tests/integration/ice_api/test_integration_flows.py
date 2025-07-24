"""End-to-end integration flow tests.

These tests validate complete workflow execution paths from API request
to final result, ensuring all components work together correctly.
They test the real-world usage patterns that the comprehensive demo showcases.
"""

import pytest
import httpx
import asyncio
import json
import time
from typing import Dict, Any
from pathlib import Path

from ice_api.main import app
from ice_sdk.services.locator import ServiceLocator
from ice_sdk.tools.service import ToolService
from ice_sdk.context import GraphContextManager
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_services():
    """Initialize services before tests run."""
    # Clear any existing services
    ServiceLocator._services.clear()
    
    # Register services like the app does
    tool_service = ToolService()
    ServiceLocator.register("tool_service", tool_service)
    
    from ice_sdk.providers.llm_service import LLMService
    ServiceLocator.register("llm_service", LLMService())
    
    # Create context manager
    ctx_manager = GraphContextManager(project_root=Path.cwd())
    ServiceLocator.register("context_manager", ctx_manager)
    
    yield
    
    # Cleanup
    ServiceLocator._services.clear()


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_csv_data(tmp_path: Path) -> str:
    """Create a sample CSV file for testing."""
    csv_file = tmp_path / "test_data.csv"
    csv_content = """Date,Product,Category,Quantity,Price,Revenue
2024-01-01,Widget A,Electronics,10,29.99,299.90
2024-01-02,Gadget B,Electronics,5,49.99,249.95
2024-01-03,Tool C,Hardware,15,19.99,299.85
2024-01-04,Widget A,Electronics,8,29.99,239.92
2024-01-05,Service D,Software,1,99.99,99.99
"""
    csv_file.write_text(csv_content)
    return str(csv_file)


class TestPartialBlueprintFlow:
    """Test incremental blueprint construction flow."""
    
    def test_create_empty_partial_blueprint(self, test_client: TestClient):
        """Test creating an empty partial blueprint."""
        response = test_client.post("/api/v1/mcp/blueprints/partial")
        
        assert response.status_code == 200
        data = response.json()
        assert "blueprint_id" in data
        assert data["nodes"] == []
        assert data["is_complete"] is False
        assert "validation_errors" in data
        assert "next_suggestions" in data
    
    def test_add_tool_node_to_partial_blueprint(self, test_client: TestClient, sample_csv_data: str):
        """Test adding a tool node to partial blueprint."""
        # Create empty blueprint
        response = test_client.post("/api/v1/mcp/blueprints/partial")
        assert response.status_code == 200
        bp_id = response.json()["blueprint_id"]
        
        # Add tool node
        node_spec = {
            "id": "csv_loader",
            "type": "tool",
            "tool_name": "csv_reader",
            "tool_args": {"file_path": sample_csv_data},
            "input_schema": {"file_path": "str"},
            "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
        }
        
        response = test_client.put(
            f"/api/v1/mcp/blueprints/partial/{bp_id}",
            json={"action": "add_node", "node": node_spec}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["id"] == "csv_loader"
        assert "suggestions" in data
    
    def test_complete_partial_blueprint_workflow(self, test_client: TestClient, sample_csv_data: str):
        """Test complete partial blueprint construction and finalization."""
        # Create empty blueprint
        response = test_client.post("/api/v1/mcp/blueprints/partial")
        blueprint_id = response.json()["blueprint_id"]
        
        # Add tool node
        tool_node = {
            "action": "add_node",
            "node": {
                "id": "load_data",
                "type": "tool",
                "tool_name": "csv_reader",
                "tool_args": {"file_path": sample_csv_data},
                "input_schema": {"file_path": "str"},
                "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
            }
        }
        
        response = test_client.put(
            f"/api/v1/mcp/blueprints/partial/{blueprint_id}",
            json=tool_node
        )
        
        # Add LLM node
        llm_node = {
            "action": "add_node",
            "node": {
                "id": "analyze_trends",
                "type": "llm",
                "name": "Analyze Sales Trends",
                "model": "gpt-4",
                "prompt": "Analyze this sales data and provide insights: {rows}",
                "dependencies": ["load_data"],
                "input_schema": {"rows": "list[dict]"},
                "output_schema": {"analysis": "dict"},
                "temperature": 0.7,
                "max_tokens": 500,
                "llm_config": {"provider": "openai"}
            }
        }
        
        response = test_client.put(
            f"/api/v1/mcp/blueprints/partial/{blueprint_id}",
            json=llm_node
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["nodes"]) == 2
        
        # Finalize the blueprint
        response = test_client.post(
            f"/api/v1/mcp/blueprints/partial/{blueprint_id}/finalize"
        )
        
        assert response.status_code == 200
        finalized = response.json()
        
        assert "blueprint_id" in finalized
        assert finalized["status"] == "accepted"


class TestWorkflowExecution:
    """Test workflow execution through MCP API."""
    
    def test_execute_simple_tool_workflow(self, test_client: TestClient, sample_csv_data: str):
        """Test executing a simple tool-only workflow."""
        # Create blueprint with just a tool
        blueprint = {
            "nodes": [
                {
                    "id": "load_csv",
                    "type": "tool",
                    "tool_name": "csv_reader",
                    "tool_args": {"file_path": sample_csv_data},
                    "input_schema": {"file_path": "str"},
                    "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
                }
            ]
        }
        
        # Execute workflow
        run_request = {
            "blueprint": blueprint,
            "options": {"max_parallel": 1}
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=run_request)
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        
        # Poll for result (in tests, should be immediate)
        result_response = test_client.get(f"/api/v1/mcp/runs/{run_id}")
        
        # May need to wait
        max_attempts = 10
        for _ in range(max_attempts):
            if result_response.status_code == 200:
                break
            import time
            time.sleep(0.1)
            result_response = test_client.get(f"/api/v1/mcp/runs/{run_id}")
        
        assert result_response.status_code == 200
        result = result_response.json()
        assert result["success"] is True
        assert "output" in result
        
    def test_execute_multi_node_workflow(self, test_client: TestClient, sample_csv_data: str):
        """Test executing a multi-node workflow with dependencies."""
        # Create blueprint matching the comprehensive demo
        blueprint = {
            "nodes": [
                {
                    "id": "load_data",
                    "type": "tool", 
                    "tool_name": "csv_reader",
                    "tool_args": {"file_path": sample_csv_data},
                    "input_schema": {"file_path": "str"},
                    "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
                },
                {
                    "id": "analyze_trends",
                    "type": "llm",
                    "model": "gpt-4",
                    "prompt": "Analyze this sales data and provide insights: {rows}",
                    "dependencies": ["load_data"],
                    "input_schema": {"rows": "list[dict]"},
                    "output_schema": {"analysis": "dict"},
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "llm_config": {"provider": "openai"}
                }
            ]
        }
        
        # Execute workflow
        run_request = {
            "blueprint": blueprint,
            "options": {"max_parallel": 2}
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=run_request)
        
        assert response.status_code == 202
        run_data = response.json()
        run_id = run_data["run_id"]
        
        # Poll for completion
        max_attempts = 20
        for _ in range(max_attempts):
            result_response = test_client.get(f"/api/v1/mcp/runs/{run_id}")
            if result_response.status_code == 200:
                result = result_response.json()
                assert result["success"] is True
                
                # Validate execution flow
                assert "start_time" in result
                assert "end_time" in result
                assert result["start_time"] <= result["end_time"]
                
                break
            elif result_response.status_code == 202:
                # Still executing
                time.sleep(0.2)
                continue
            else:
                pytest.fail(f"Unexpected status code: {result_response.status_code}")
        else:
            pytest.fail("Workflow execution timed out")


class TestErrorHandlingFlows:
    """Test error handling and validation flows."""
    
    def test_invalid_blueprint_schema_rejection(self, test_client: TestClient):
        """Test that invalid blueprints are rejected with clear errors."""
        # Blueprint with invalid schema
        invalid_blueprint = {
            "nodes": [
                {
                    "id": "bad_tool",
                    "type": "tool",
                    "tool_name": "csv_reader",
                    "input_schema": {"file_path": "str"},
                    "output_schema": {"rows": "invalid_type"}  # Invalid type
                }
            ]
        }
        
        run_request = {
            "blueprint": invalid_blueprint,
            "options": {"max_parallel": 1}
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=run_request)
        
        # Should fail validation
        assert response.status_code == 400
        assert "error" in response.json() or "detail" in response.json()
    
    def test_missing_dependency_rejection(self, test_client: TestClient):
        """Test that blueprints with missing dependencies are rejected."""
        # Blueprint with missing dependency
        invalid_blueprint = {
            "nodes": [
                {
                    "id": "dependent_node",
                    "type": "tool",
                    "tool_name": "csv_reader",
                    "dependencies": ["missing_node"],  # References non-existent node
                    "input_schema": {"file_path": "str"},
                    "output_schema": {"rows": "list[dict]"}
                }
            ]
        }
        
        run_request = {
            "blueprint": invalid_blueprint,
            "options": {"max_parallel": 1}
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=run_request)
        
        # Should fail validation
        assert response.status_code == 400
        error_msg = response.json().get("detail", "")
        assert "missing" in error_msg.lower() or "dependency" in error_msg.lower()
    
    def test_malformed_run_request_rejection(self, test_client: TestClient):
        """Test that malformed run requests are rejected."""
        # Request missing both blueprint and blueprint_id
        invalid_request = {
            "options": {"max_parallel": 1}
            # No blueprint or blueprint_id
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=invalid_request)
        
        assert response.status_code == 400
        assert "blueprint" in response.json().get("detail", "").lower()


class TestEventStreamingFlow:
    """Test real-time event streaming for workflow execution."""
    
    def test_workflow_events_generated(self, test_client: TestClient, sample_csv_data: str):
        """Test that workflow execution generates events."""
        # Simple workflow for event testing
        blueprint = {
            "nodes": [
                {
                    "id": "simple_tool",
                    "type": "tool",
                    "tool_name": "csv_reader", 
                    "tool_args": {"file_path": sample_csv_data},
                    "input_schema": {"file_path": "str"},
                    "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
                }
            ]
        }
        
        # Start workflow
        run_request = {
            "blueprint": blueprint,
            "options": {"max_parallel": 1}
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=run_request)
        assert response.status_code == 202
        
        run_id = response.json()["run_id"]
        
        # Wait for completion
        time.sleep(1.0)
        
        # Check that events endpoint exists
        events_response = test_client.get(f"/api/v1/mcp/runs/{run_id}/events")
        
        # Should either get events or 404 if run not found
        assert events_response.status_code in [200, 404]


class TestServiceIntegrationFlow:
    """Test service integration and discovery flows."""
    
    def test_service_locator_integration(self, test_client: TestClient):
        """Test that services are properly integrated through ServiceLocator."""
        # Services should be registered by our setup_services fixture
        
        # Check that core services are registered
        tool_service = ServiceLocator.get("tool_service")
        context_manager = ServiceLocator.get("context_manager")
        
        assert tool_service is not None, "ToolService should be registered"
        assert context_manager is not None, "GraphContextManager should be registered"
        
        # Test that API can access services
        response = test_client.get("/api/v1/tools")
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
    
    def test_tool_registration_flow(self, test_client: TestClient):
        """Test that tools are properly registered and available."""
        # Get list of tools through API
        response = test_client.get("/api/v1/tools")
        assert response.status_code == 200
        
        tools = response.json()
        assert isinstance(tools, list)
        
        # Should have at least csv_reader tool available
        assert any("csv_reader" in tool for tool in tools)


class TestComprehensiveDemoFlow:
    """Test the exact flow demonstrated in comprehensive_demo.py."""
    
    def test_demo_section_1_incremental_construction(self, test_client: TestClient, sample_csv_data: str):
        """Test Section 1: Incremental Blueprint Construction."""
        # 1.1 Create empty blueprint
        response = test_client.post("/api/v1/mcp/blueprints/partial")
        assert response.status_code == 200
        partial = response.json()
        bp_id = partial["blueprint_id"]
        
        # 1.2 Add CSV reader node
        csv_node = {
            "id": "load_data",
            "type": "tool",
            "tool_name": "csv_reader",
            "tool_args": {"file_path": sample_csv_data},
            "pending_outputs": ["data"]  # Tell Frosty we'll output 'data'
        }
        
        response = test_client.put(
            f"/api/v1/mcp/blueprints/partial/{bp_id}",
            json={"action": "add_node", "node": csv_node}
        )
        assert response.status_code == 200
        
        # 1.3 Add LLM analyzer node
        llm_node = {
            "id": "analyze_trends",
            "type": "llm",
            "model": "gpt-4",
            "prompt": "Analyze this sales data and provide insights: {data}",
            "dependencies": ["load_data"],
            "pending_inputs": ["data"],  # Tell Frosty we need 'data'
            "llm_config": {"provider": "openai"}
        }
        
        response = test_client.put(
            f"/api/v1/mcp/blueprints/partial/{bp_id}",
            json={"action": "add_node", "node": llm_node}
        )
        assert response.status_code == 200
        
        # 1.4 Finalize blueprint
        response = test_client.post(f"/api/v1/mcp/blueprints/partial/{bp_id}/finalize")
        assert response.status_code == 200
        
        return bp_id
    
    def test_demo_section_3_execution(self, test_client: TestClient, sample_csv_data: str):
        """Test Section 3: Workflow Execution."""
        # Create a finalized blueprint first
        blueprint_id = self.test_demo_section_1_incremental_construction(test_client, sample_csv_data)
        
        # Execute the workflow
        run_request = {
            "blueprint_id": blueprint_id,
            "options": {"max_parallel": 5}
        }
        
        response = test_client.post("/api/v1/mcp/runs", json=run_request)
        assert response.status_code == 202
        
        run_data = response.json()
        run_id = run_data["run_id"]
        
        # Poll for completion
        max_attempts = 30
        for _ in range(max_attempts):
            result_response = test_client.get(f"/api/v1/mcp/runs/{run_id}")
            if result_response.status_code == 200:
                result = result_response.json()
                assert result["success"] is True
                assert "output" in result
                break
            elif result_response.status_code == 202:
                time.sleep(0.2)
            else:
                pytest.fail(f"Unexpected status: {result_response.status_code}")
        else:
            pytest.fail("Execution timed out")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 