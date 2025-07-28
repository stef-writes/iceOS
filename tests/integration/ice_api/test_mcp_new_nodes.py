"""MCP integration tests for new Phase 2 node types."""

import pytest
import json
from fastapi.testclient import TestClient

from ice_core.models.mcp import Blueprint, NodeSpec
from ice_api.main import app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


def test_mcp_swarm_blueprint_validation(client: TestClient):
    """MCP validates swarm blueprints correctly."""
    blueprint_data = {
        "blueprint_id": "test_swarm_blueprint",
        "nodes": [
            {
                "id": "investment_swarm",
                "type": "swarm",
                "agents": [
                    {"package": "analyst", "role": "financial_analyst"},
                    {"package": "critic", "role": "risk_assessor"}
                ],
                "coordination_strategy": "consensus"
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    
    assert response.status_code == 201
    result = response.json()
    assert result["blueprint_id"] == "test_swarm_blueprint"
    assert result["status"] == "success"


def test_mcp_human_blueprint_validation(client: TestClient):
    """MCP validates human-in-the-loop blueprints correctly."""
    blueprint_data = {
        "blueprint_id": "test_human_blueprint",
        "nodes": [
            {
                "id": "approval_gate",
                "type": "human",
                "prompt_message": "Please review and approve this investment decision",
                "approval_type": "approve_reject",
                "timeout_seconds": 1800
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    
    assert response.status_code == 201
    result = response.json()
    assert result["blueprint_id"] == "test_human_blueprint"
    assert result["status"] == "success"


def test_mcp_monitor_blueprint_validation(client: TestClient):
    """MCP validates monitoring blueprints correctly."""
    blueprint_data = {
        "blueprint_id": "test_monitor_blueprint",
        "nodes": [
            {
                "id": "cost_monitor",
                "type": "monitor",
                "metric_expression": "cost > 100 OR latency > 30",
                "action_on_trigger": "pause",
                "alert_channels": ["email", "slack"]
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    
    assert response.status_code == 201
    result = response.json()
    assert result["blueprint_id"] == "test_monitor_blueprint"
    assert result["status"] == "success"


def test_mcp_swarm_blueprint_execution(client: TestClient):
    """MCP executes swarm blueprints correctly."""
    # First create the blueprint
    blueprint_data = {
        "blueprint_id": "execution_test_swarm",
        "nodes": [
            {
                "id": "test_swarm",
                "type": "swarm",
                "agents": [
                    {"package": "test.analyst", "role": "analyst"},
                    {"package": "test.critic", "role": "critic"}
                ],
                "coordination_strategy": "consensus"
            }
        ]
    }
    
    create_response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    assert create_response.status_code == 201
    
    # Execute the blueprint
    run_data = {
        "blueprint_id": "execution_test_swarm",
        "inputs": {"context": "Test swarm coordination"}
    }
    
    run_response = client.post("/api/v1/mcp/runs", json=run_data)
    assert run_response.status_code == 202
    
    run_result = run_response.json()
    assert "run_id" in run_result
    assert run_result["status"] == "accepted"


def test_mcp_human_blueprint_execution(client: TestClient):
    """MCP executes human-in-the-loop blueprints correctly."""
    blueprint_data = {
        "blueprint_id": "execution_test_human",
        "nodes": [
            {
                "id": "test_human",
                "type": "human",
                "prompt_message": "Please approve this test action",
                "approval_type": "approve_reject"
            }
        ]
    }
    
    create_response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    assert create_response.status_code == 201
    
    run_data = {
        "blueprint_id": "execution_test_human", 
        "inputs": {"action": "Test human approval"}
    }
    
    run_response = client.post("/api/v1/mcp/runs", json=run_data)
    assert run_response.status_code == 202
    
    run_result = run_response.json()
    assert "run_id" in run_result


def test_mcp_monitor_blueprint_execution(client: TestClient):
    """MCP executes monitoring blueprints correctly."""
    blueprint_data = {
        "blueprint_id": "execution_test_monitor",
        "nodes": [
            {
                "id": "test_monitor",
                "type": "monitor",
                "metric_expression": "cost > 50",
                "action_on_trigger": "alert_only"
            }
        ]
    }
    
    create_response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    assert create_response.status_code == 201
    
    run_data = {
        "blueprint_id": "execution_test_monitor",
        "inputs": {"cost": 75, "latency": 20}
    }
    
    run_response = client.post("/api/v1/mcp/runs", json=run_data)
    assert run_response.status_code == 202
    
    run_result = run_response.json()
    assert "run_id" in run_result


def test_mcp_jsonrpc_swarm_tool_call(client: TestClient):
    """MCP JSON-RPC API handles swarm tool calls."""
    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "swarm:consensus",
            "arguments": {
                "agents": [
                    {"package": "test.analyst", "role": "analyst"},
                    {"package": "test.critic", "role": "critic"}
                ],
                "strategy": "consensus"
            }
        }
    }
    
    response = client.post("/api/mcp", json=request_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == 1
    assert "result" in result


def test_mcp_jsonrpc_human_tool_call(client: TestClient):
    """MCP JSON-RPC API handles human tool calls."""
    request_data = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "human:approval",
            "arguments": {
                "prompt": "Please approve this test action",
                "approval_type": "approve_reject"
            }
        }
    }
    
    response = client.post("/api/mcp", json=request_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == 2
    assert "result" in result


def test_mcp_jsonrpc_monitor_tool_call(client: TestClient):
    """MCP JSON-RPC API handles monitor tool calls."""
    request_data = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "monitor:metrics",
            "arguments": {
                "metric_expression": "cost > 100",
                "action": "alert_only"
            }
        }
    }
    
    response = client.post("/api/mcp", json=request_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == 3
    assert "result" in result


def test_mcp_jsonrpc_tools_list_includes_new_nodes(client: TestClient):
    """MCP JSON-RPC tools list includes new Phase 2 node types."""
    request_data = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/list",
        "params": {}
    }
    
    response = client.post("/api/mcp", json=request_data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert "result" in result
    
    tools = result["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    
    # Check that our new node types are included
    assert "swarm:consensus" in tool_names
    assert "human:approval" in tool_names
    assert "monitor:metrics" in tool_names


def test_mcp_invalid_swarm_blueprint_validation_error(client: TestClient):
    """MCP properly validates and rejects invalid swarm blueprints."""
    invalid_blueprint = {
        "blueprint_id": "invalid_swarm",
        "nodes": [
            {
                "id": "bad_swarm",
                "type": "swarm",
                "agents": [
                    {"package": "single_agent", "role": "lonely"}
                    # Only one agent - should fail validation
                ]
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=invalid_blueprint)
    
    assert response.status_code == 400
    result = response.json()
    assert "detail" in result


def test_mcp_invalid_human_blueprint_validation_error(client: TestClient):
    """MCP properly validates and rejects invalid human blueprints."""
    invalid_blueprint = {
        "blueprint_id": "invalid_human",
        "nodes": [
            {
                "id": "bad_human",
                "type": "human",
                "prompt_message": ""  # Empty prompt - should fail validation
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=invalid_blueprint)
    
    assert response.status_code == 400


def test_mcp_invalid_monitor_blueprint_validation_error(client: TestClient):
    """MCP properly validates and rejects invalid monitor blueprints."""
    invalid_blueprint = {
        "blueprint_id": "invalid_monitor",
        "nodes": [
            {
                "id": "bad_monitor",
                "type": "monitor",
                "metric_expression": ""  # Empty expression - should fail validation
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=invalid_blueprint)
    
    assert response.status_code == 400 