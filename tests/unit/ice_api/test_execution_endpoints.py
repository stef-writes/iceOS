import types
from unittest.mock import AsyncMock, Mock, patch
import asyncio
import os

import pytest
from fastapi.testclient import TestClient

# Disable Redis for tests by setting a flag
os.environ["TESTING"] = "true"

from ice_api.main import app
from ice_sdk.registry.agent import global_agent_registry
from ice_sdk.registry.unit import global_unit_registry
from ice_sdk.registry.chain import global_chain_registry
from ice_sdk.services.initialization import initialize_services
from ice_sdk.services.locator import ServiceLocator


# Dummy implementations ------------------------------------------------------


class _DummyAgent:
    name = "dummy_agent"

    async def execute(self, payload):
        return {"agent": payload}


class _DummyUnit:
    name = "dummy_unit"

    async def execute(self, payload):
        return {"unit": payload}


class _DummyChain:
    async def run(self, ctx):
        return {"chain": ctx}


# One-time registration ------------------------------------------------------

if "dummy_agent" not in [n for n, _ in global_agent_registry]:
    # Register as import path for agent registry
    global_agent_registry.register("dummy_agent", "tests.unit.ice_api.test_execution_endpoints._DummyAgent")

if "dummy_unit" not in [n for n, _ in global_unit_registry]:
    global_unit_registry.register("dummy_unit", _DummyUnit())

if "dummy_chain" not in [n for n, _ in global_chain_registry]:
    global_chain_registry.register("dummy_chain", _DummyChain())


# Initialize services before creating test client
initialize_services()

# Mock workflow service for direct execution endpoints
mock_workflow_service = Mock()
mock_workflow_service.execute = AsyncMock(return_value={
    "success": True,
    "output": {"result": "mocked"},
    "error": None
})
ServiceLocator.register("workflow_service", mock_workflow_service)

# Mock the start_run function to avoid Redis calls
async def mock_start_run(request):
    """Mock start_run that returns immediately without using Redis."""
    from ice_core.models.mcp import RunAck
    return RunAck(
        run_id="test_run_123",
        events_endpoint="/api/v1/mcp/runs/test_run_123/events"
    )

# Mock wait_for_run_completion for synchronous execution
async def mock_wait_for_completion(run_id, timeout):
    """Mock waiting for run completion."""
    return {
        "status": "completed",
        "output": {"hello": "world"},
        "error": None
    }

# Apply the mocks
with patch('ice_api.api.mcp.start_run', mock_start_run):
    with patch('ice_api.api.direct_execution.wait_for_run_completion', mock_wait_for_completion):
        # Create test client with mocked functions
        client = TestClient(app)


@pytest.mark.parametrize(
    "path, payload, expected_status",
    [
        ("agents/dummy_agent", {"inputs": {"foo": "bar"}}, 200),  # Direct execution waits by default
        ("tools/csv_reader", {"inputs": {"file_path": "test.csv"}}, 200),
        ("chains/dummy_chain", {"inputs": {"y": 2}}, 200),
    ],
)
def test_execute_endpoints(path, payload, expected_status):
    resp = client.post(f"/v1/{path}", json=payload)
    
    # Debug print to see what's happening
    if resp.status_code != expected_status:
        print(f"Expected {expected_status}, got {resp.status_code}")
        print(f"Response: {resp.json()}")
    
    # Direct execution endpoints return 200 OK when wait_for_completion=True (default)
    assert resp.status_code == expected_status
    
    # Check response structure
    data = resp.json()
    assert "run_id" in data
    assert "status" in data
    assert "telemetry_url" in data
    
    # When waiting for completion, status should be "completed" or "failed"
    assert data["status"] in ["completed", "failed"]


@pytest.mark.parametrize(
    "path, payload",
    [
        ("agents/dummy_agent", {"inputs": {"foo": "bar"}, "wait_for_completion": False}),
        ("tools/csv_reader", {"inputs": {"file_path": "test.csv"}, "wait_for_completion": False}),
        ("chains/dummy_chain", {"inputs": {"y": 2}, "wait_for_completion": False}),
    ],
)
def test_execute_endpoints_async(path, payload):
    """Test async execution returns 202 Accepted."""
    resp = client.post(f"/v1/{path}", json=payload)
    
    # Async execution should return 202 Accepted
    assert resp.status_code == 202
    
    # Check response structure
    data = resp.json()
    assert "run_id" in data
    assert "status" in data
    assert "telemetry_url" in data
    
    # When not waiting, status should be "running"
    assert data["status"] == "running" 