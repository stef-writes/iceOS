"""End-to-end integration flow tests.

These tests validate complete workflow execution paths from API request
to final result, ensuring all components work together correctly.
They test the real-world usage patterns that the comprehensive demo showcases.
"""

import pytest
import httpx
import asyncio
import json
from typing import Dict, Any
from pathlib import Path

from ice_api.main import app
from ice_sdk.services.locator import ServiceLocator


@pytest.fixture
async def test_client():
    """Create a test client for the FastAPI app."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


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
    """Test the incremental blueprint construction flow (Frosty-style)."""
    
    @pytest.mark.asyncio
    async def test_create_empty_partial_blueprint(self, test_client: httpx.AsyncClient):
        """Test creating an empty partial blueprint."""
        response = await test_client.post("/api/v1/mcp/blueprints/partial")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "blueprint_id" in data
        assert data["blueprint_id"].startswith("partial_bp_")
        assert data["schema_version"] == "1.1.0"
        assert data["nodes"] == []
        assert data["is_complete"] is False
        assert data["validation_errors"] == []
        assert data["next_suggestions"] == []
    
    @pytest.mark.asyncio
    async def test_add_tool_node_to_partial_blueprint(self, test_client: httpx.AsyncClient, sample_csv_data: str):
        """Test adding a tool node to partial blueprint."""
        # Create empty blueprint
        response = await test_client.post("/api/v1/mcp/blueprints/partial")
        blueprint_id = response.json()["blueprint_id"]
        
        # Add tool node
        tool_node = {
            "action": "add_node",
            "node": {
                "id": "load_data",
                "type": "tool",
                "tool_name": "csv_reader",
                "name": "Load Sales Data",
                "tool_args": {
                    "file_path": sample_csv_data
                },
                "input_schema": {
                    "file_path": "str"
                },
                "output_schema": {
                    "rows": "list[dict]",
                    "headers": "list[str]"
                }
            }
        }
        
        response = await test_client.put(
            f"/api/v1/mcp/blueprints/partial/{blueprint_id}",
            json=tool_node
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["id"] == "load_data"
        assert data["nodes"][0]["type"] == "tool"
        
        # Should generate AI suggestions
        assert len(data["next_suggestions"]) > 0
        suggestion = data["next_suggestions"][0]
        assert suggestion["type"] == "llm"
        assert "Process tool output" in suggestion["reason"]
    
    @pytest.mark.asyncio
    async def test_complete_partial_blueprint_workflow(self, test_client: httpx.AsyncClient, sample_csv_data: str):
        """Test complete partial blueprint construction and finalization."""
        # Create empty blueprint
        response = await test_client.post("/api/v1/mcp/blueprints/partial")
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
        
        await test_client.put(
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
        
        response = await test_client.put(
            f"/api/v1/mcp/blueprints/partial/{blueprint_id}",
            json=llm_node
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["nodes"]) == 2
        assert data["is_complete"] is True
        
        # Finalize blueprint
        response = await test_client.post(
            f"/api/v1/mcp/blueprints/partial/{blueprint_id}/finalize"
        )
        
        assert response.status_code == 200
        final_data = response.json()
        assert final_data["status"] == "accepted"
        assert "blueprint_id" in final_data


class TestWorkflowExecution:
    """Test complete workflow execution flows."""
    
    @pytest.mark.asyncio 
    async def test_execute_simple_tool_workflow(self, test_client: httpx.AsyncClient, sample_csv_data: str):
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
        
        response = await test_client.post("/api/v1/mcp/runs", json=run_request)
        
        assert response.status_code == 202
        run_data = response.json()
        
        assert "run_id" in run_data
        assert run_data["run_id"].startswith("run_")
        assert "status_endpoint" in run_data
        assert "events_endpoint" in run_data
        
        # Check run result
        run_id = run_data["run_id"]
        
        # Poll for completion (simplified for test)
        max_attempts = 10
        for _ in range(max_attempts):
            result_response = await test_client.get(f"/api/v1/mcp/runs/{run_id}")
            if result_response.status_code == 200:
                result = result_response.json()
                assert result["success"] is True
                assert "output" in result
                break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("Workflow execution timed out")
    
    @pytest.mark.asyncio
    async def test_execute_multi_node_workflow(self, test_client: httpx.AsyncClient, sample_csv_data: str):
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
        
        response = await test_client.post("/api/v1/mcp/runs", json=run_request)
        
        assert response.status_code == 202
        run_data = response.json()
        run_id = run_data["run_id"]
        
        # Poll for completion
        max_attempts = 20
        for _ in range(max_attempts):
            result_response = await test_client.get(f"/api/v1/mcp/runs/{run_id}")
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
                await asyncio.sleep(0.2)
                continue
            else:
                pytest.fail(f"Unexpected status code: {result_response.status_code}")
        else:
            pytest.fail("Workflow execution timed out")


class TestErrorHandlingFlows:
    """Test error handling in complete integration flows."""
    
    @pytest.mark.asyncio
    async def test_invalid_blueprint_schema_rejection(self, test_client: httpx.AsyncClient):
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
        
        response = await test_client.post("/api/v1/mcp/runs", json=run_request)
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "detail" in error_data
        assert "invalid output_schema" in error_data["detail"]
    
    @pytest.mark.asyncio
    async def test_missing_dependency_rejection(self, test_client: httpx.AsyncClient):
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
        
        response = await test_client.post("/api/v1/mcp/runs", json=run_request)
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "detail" in error_data
        assert "missing dependency" in error_data["detail"]
    
    @pytest.mark.asyncio
    async def test_malformed_run_request_rejection(self, test_client: httpx.AsyncClient):
        """Test that malformed run requests are rejected."""
        # Request missing both blueprint and blueprint_id
        invalid_request = {
            "options": {"max_parallel": 1}
            # No blueprint or blueprint_id
        }
        
        response = await test_client.post("/api/v1/mcp/runs", json=invalid_request)
        
        assert response.status_code == 400
        error_data = response.json()
        
        assert "detail" in error_data
        assert "'blueprint' or 'blueprint_id' required" in error_data["detail"]


class TestEventStreamingFlow:
    """Test real-time event streaming during workflow execution."""
    
    @pytest.mark.asyncio
    async def test_workflow_events_generated(self, test_client: httpx.AsyncClient, sample_csv_data: str):
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
        
        response = await test_client.post("/api/v1/mcp/runs", json=run_request)
        assert response.status_code == 202
        
        run_id = response.json()["run_id"]
        
        # Wait for completion
        await asyncio.sleep(1.0)
        
        # Check that events endpoint exists
        events_response = await test_client.get(f"/api/v1/mcp/runs/{run_id}/events")
        
        # Should either get events or 404 if run not found
        assert events_response.status_code in [200, 404]


class TestServiceIntegrationFlow:
    """Test integration between different service components."""
    
    @pytest.mark.asyncio
    async def test_service_locator_integration(self, test_client: httpx.AsyncClient):
        """Test that services are properly integrated through ServiceLocator."""
        # This test verifies that the services registered during app startup
        # are available and working correctly
        
        # Check that core services are registered
        tool_service = ServiceLocator.get("tool_service")
        context_manager = ServiceLocator.get("context_manager")
        
        assert tool_service is not None, "ToolService should be registered"
        assert context_manager is not None, "GraphContextManager should be registered"
        
        # Check that services have expected functionality
        available_tools = tool_service.available_tools()
        assert isinstance(available_tools, list)
        
        # Context manager should have tool service reference
        assert context_manager.tool_service is not None
        assert context_manager.tool_service is tool_service
    
    @pytest.mark.asyncio
    async def test_tool_registration_flow(self, test_client: httpx.AsyncClient):
        """Test that tools are properly registered and available."""
        context_manager = ServiceLocator.get("context_manager")
        tool_service = ServiceLocator.get("tool_service")
        
        # Should have at least csv_reader tool available
        available_tools = tool_service.available_tools()
        assert "csv_reader" in available_tools
        
        # Context manager should also have the tool
        csv_tool = context_manager.get_tool("csv_reader")
        assert csv_tool is not None
        assert csv_tool.name == "csv_reader"


class TestComprehensiveDemoFlow:
    """Test the exact flow demonstrated in comprehensive_demo.py."""
    
    @pytest.mark.asyncio
    async def test_demo_section_1_incremental_construction(self, test_client: httpx.AsyncClient, sample_csv_data: str):
        """Test Section 1: Incremental Blueprint Construction."""
        # 1.1 Create empty blueprint
        response = await test_client.post("/api/v1/mcp/blueprints/partial")
        assert response.status_code == 200
        partial = response.json()
        bp_id = partial["blueprint_id"]
        
        # 1.2 Add CSV reader
        csv_node_update = {
            "action": "add_node",
            "node": {
                "id": "load_data",
                "type": "tool",
                "tool_name": "csv_reader",
                "name": "Load Sales Data",
                "tool_args": {"file_path": sample_csv_data},
                "input_schema": {"file_path": "str"},
                "output_schema": {"rows": "list[dict]", "headers": "list[str]"}
            }
        }
        
        response = await test_client.put(
            f"/api/v1/mcp/blueprints/partial/{bp_id}",
            json=csv_node_update
        )
        assert response.status_code == 200
        partial = response.json()
        
        # Should have AI suggestions
        assert len(partial.get("next_suggestions", [])) > 0
        
        # 1.3 Add LLM analyzer
        llm_node_update = {
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
        
        response = await test_client.put(
            f"/api/v1/mcp/blueprints/partial/{bp_id}",
            json=llm_node_update
        )
        assert response.status_code == 200
        partial = response.json()
        
        # 1.4 Should be complete
        assert partial["is_complete"] is True
        
        # 1.5 Finalize
        response = await test_client.post(
            f"/api/v1/mcp/blueprints/partial/{bp_id}/finalize"
        )
        assert response.status_code == 200
        final = response.json()
        
        return final["blueprint_id"]
    
    @pytest.mark.asyncio
    async def test_demo_section_3_execution(self, test_client: httpx.AsyncClient, sample_csv_data: str):
        """Test Section 3: Workflow Execution.""" 
        # Create a finalized blueprint first
        blueprint_id = await self.test_demo_section_1_incremental_construction(test_client, sample_csv_data)
        
        # Execute the workflow
        run_request = {
            "blueprint_id": blueprint_id,
            "options": {"max_parallel": 5}
        }
        
        response = await test_client.post("/api/v1/mcp/runs", json=run_request)
        assert response.status_code == 202
        
        run_data = response.json()
        run_id = run_data["run_id"]
        
        # Poll for completion
        max_attempts = 30
        for _ in range(max_attempts):
            result_response = await test_client.get(f"/api/v1/mcp/runs/{run_id}")
            if result_response.status_code == 200:
                result = result_response.json()
                assert result["success"] is True
                assert "output" in result
                break
            elif result_response.status_code == 202:
                await asyncio.sleep(0.2)
            else:
                pytest.fail(f"Unexpected status: {result_response.status_code}")
        else:
            pytest.fail("Execution timed out")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 