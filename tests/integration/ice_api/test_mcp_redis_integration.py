"""Integration tests for MCP API with real Redis instance.

These tests verify the MCP API functionality using a real Redis container
instead of in-memory stubs.
"""

import asyncio
import json
from typing import Any, Dict

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.initialization import initialize_services
from ice_sdk.services.locator import ServiceLocator


pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def initialize_app(redis_url: str):
    """Initialize the application with the test Redis URL."""
    import os
    os.environ["REDIS_URL"] = redis_url
    
    # Reset the Redis client to use the new URL
    import ice_api.redis_client as _rc
    _rc._redis_client = None  # Force recreation with new URL
    
    # Initialize services
    initialize_services()
    
    yield
    
    # Cleanup
    ServiceLocator.clear()
    _rc._redis_client = None  # Reset for next test


@pytest.mark.asyncio
async def test_mcp_blueprint_workflow_with_redis(redis_client, redis_url):
    """Test MCP blueprint creation and execution with real Redis."""
    client = TestClient(app)
    
    # Create a blueprint
    blueprint_data = {
        "schema_version": "1.1.0",
        "name": "test-workflow",
        "description": "Integration test workflow",
        "nodes": [
            {
                "id": "sleep_1",
                "type": "tool",
                "tool_name": "sleep",
                "tool_args": {"duration": 0.1},
                "input_schema": {"type": "object", "properties": {"duration": {"type": "number"}}},
                "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
            },
            {
                "id": "sleep_2", 
                "type": "tool",
                "tool_name": "sleep",
                "tool_args": {"duration": 0.1},
                "dependencies": ["sleep_1"],
                "input_schema": {"type": "object", "properties": {"duration": {"type": "number"}}},
                "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
            }
        ]
    }
    
    # Register the blueprint
    response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    assert response.status_code == 201
    blueprint_id = response.json()["blueprint_id"]
    
    # Verify blueprint is stored in Redis
    stored_blueprint = await redis_client.hget(f"blueprint:{blueprint_id}", "json")
    assert stored_blueprint is not None
    assert json.loads(stored_blueprint)["name"] == "test-workflow"
    
    # Execute the workflow
    run_response = client.post(
        "/api/v1/mcp/runs",
        json={
            "blueprint_id": blueprint_id,
            "context": {"test": "data"}
        }
    )
    assert run_response.status_code == 202
    run_id = run_response.json()["run_id"]
    
    # Check event stream in Redis
    await asyncio.sleep(0.5)  # Allow time for execution
    
    # Read events from Redis stream
    events = await redis_client.xread({f"run:{run_id}:events": "0"}, count=10)
    assert len(events) > 0
    
    # Verify event structure
    stream_name, messages = events[0]
    assert stream_name == f"run:{run_id}:events"
    
    # Check for specific event types
    event_types = [json.loads(msg[1]["data"])["event"] for _, msg in messages]
    assert "workflow.started" in event_types
    assert "workflow.completed" in event_types


@pytest.mark.asyncio 
async def test_mcp_event_streaming_with_redis(redis_client, redis_url):
    """Test MCP event streaming functionality with real Redis."""
    client = TestClient(app)
    
    # Create and register a simple blueprint
    blueprint_data = {
        "schema_version": "1.1.0",
        "name": "event-test",
        "nodes": [
            {
                "id": "test_node",
                "type": "tool", 
                "tool_name": "sleep",
                "tool_args": {"duration": 0.05},
                "input_schema": {"type": "object", "properties": {"duration": {"type": "number"}}},
                "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
            }
        ]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    blueprint_id = response.json()["blueprint_id"]
    
    # Start workflow execution
    run_response = client.post(
        "/api/v1/mcp/runs",
        json={"blueprint_id": blueprint_id, "context": {}}
    )
    run_id = run_response.json()["run_id"]
    
    # Poll for events via SSE endpoint
    with client.stream("GET", f"/api/v1/mcp/runs/{run_id}/events") as stream:
        events_received = []
        for chunk in stream.iter_text():
            if chunk.strip() and chunk.startswith("data:"):
                event_data = json.loads(chunk[5:])
                events_received.append(event_data)
                
                # Stop after receiving completion event
                if event_data.get("event") == "workflow.completed":
                    break
    
    # Verify we received the expected events
    event_types = [e["event"] for e in events_received]
    assert "workflow.started" in event_types
    assert "node.started" in event_types  
    assert "node.completed" in event_types
    assert "workflow.completed" in event_types


@pytest.mark.asyncio
async def test_blueprint_persistence_across_restarts(redis_client, redis_url):
    """Test that blueprints persist in Redis across application restarts."""
    client = TestClient(app)
    
    # Create blueprint
    blueprint_data = {
        "schema_version": "1.1.0",
        "name": "persistent-workflow",
                    "nodes": [{
                "id": "node1", 
                "type": "tool", 
                "tool_name": "sleep", 
                "tool_args": {"duration": 0.01},
                "input_schema": {"type": "object", "properties": {"duration": {"type": "number"}}},
                "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
            }]
    }
    
    response = client.post("/api/v1/mcp/blueprints", json=blueprint_data)
    blueprint_id = response.json()["blueprint_id"]
    
    # Verify it's in Redis
    stored = await redis_client.hget(f"blueprint:{blueprint_id}", "json")
    assert stored is not None
    
    # Simulate app restart by clearing ServiceLocator
    ServiceLocator.clear()
    initialize_services()
    
    # Create new client and verify blueprint still exists
    new_client = TestClient(app)
    get_response = new_client.get(f"/api/v1/mcp/blueprints/{blueprint_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "persistent-workflow" 