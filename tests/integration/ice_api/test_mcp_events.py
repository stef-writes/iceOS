"""Integration tests for MCP event streaming with real Redis."""

import asyncio
import json
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.locator import ServiceLocator


pytestmark = [pytest.mark.integration]


class _DummyWorkflowService:
    """Stub workflow service that emits simple events."""
    
    async def execute(
        self,
        nodes: list[Any],
        name: str,
        max_parallel: int = 5,
        *,
        run_id: str | None = None,
        event_emitter=None,
    ) -> Dict[str, Any]:
        # Emit events to simulate workflow lifecycle
        if event_emitter:
            event_emitter("workflow.started", {"run_id": run_id})
            await asyncio.sleep(0.01)  # Simulate work
            event_emitter("node.started", {"node_id": "test_node"})
            await asyncio.sleep(0.01)
            event_emitter("node.completed", {"node_id": "test_node"})
            event_emitter("workflow.completed", {"run_id": run_id})
        
        return {"success": True, "output": {"result": "test"}}


@pytest.fixture(autouse=True)
def setup_test_env(redis_url: str):
    """Set up test environment with Redis URL and stub workflow service."""
    import os
    os.environ["REDIS_URL"] = redis_url
    
    # Register stub workflow service
    ServiceLocator.register("workflow_service", _DummyWorkflowService())
    
    yield
    
    # Cleanup
    ServiceLocator.clear()


@pytest.mark.asyncio
async def test_event_streaming_basic(redis_client):
    """Test basic event streaming functionality."""
    client = TestClient(app)
    
    # Create a simple blueprint
    blueprint = {
        "schema_version": "1.1.0",
        "name": "test-events",
        "nodes": [{
            "id": "n1", 
            "type": "tool", 
            "tool_name": "sleep", 
            "tool_args": {"duration": 0.01},
            "input_schema": {"type": "object", "properties": {"duration": {"type": "number"}}},
            "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
        }]
    }
    
    # Start run
    run_resp = client.post("/api/v1/mcp/runs", json={"blueprint": blueprint})
    assert run_resp.status_code == 202
    run_id = run_resp.json()["run_id"]
    
    # Allow time for events to be written
    await asyncio.sleep(0.1)
    
    # Check events in Redis
    events = await redis_client.xread({f"run:{run_id}:events": "0"}, count=10)
    assert len(events) > 0
    
    # Parse event data
    stream_name, messages = events[0]
    event_types = []
    for _, msg in messages:
        event_data = json.loads(msg["data"])
        event_types.append(event_data["event"])
    
    # Verify expected events
    assert "workflow.started" in event_types
    assert "workflow.completed" in event_types


@pytest.mark.asyncio
async def test_event_sse_endpoint(redis_client):
    """Test Server-Sent Events endpoint for event streaming."""
    client = TestClient(app)
    
    # Register a blueprint first
    blueprint = {
        "schema_version": "1.1.0", 
        "name": "sse-test",
        "nodes": [{"id": "n1", "type": "llm", "model": "gpt-4o", "prompt": "Hi", "llm_config": {"provider": "openai"}}]
    }
    
    reg_resp = client.post("/api/v1/mcp/blueprints", json=blueprint)
    blueprint_id = reg_resp.json()["blueprint_id"]
    
    # Start workflow
    run_resp = client.post("/api/v1/mcp/runs", json={"blueprint_id": blueprint_id})
    run_id = run_resp.json()["run_id"]
    
    # Stream events via SSE
    events_received = []
    with client.stream("GET", f"/api/v1/mcp/runs/{run_id}/events") as stream:
        for chunk in stream.iter_text():
            if chunk.strip() and chunk.startswith("data:"):
                try:
                    event_data = json.loads(chunk[5:])
                    events_received.append(event_data)
                    
                    # Stop after workflow completes
                    if event_data.get("event") == "workflow.completed":
                        break
                except json.JSONDecodeError:
                    continue
    
    # Verify we got events
    assert len(events_received) > 0
    event_types = [e["event"] for e in events_received]
    assert "workflow.started" in event_types
    assert "workflow.completed" in event_types


@pytest.mark.asyncio
async def test_concurrent_event_streams(redis_client):
    """Test multiple concurrent workflow event streams."""
    client = TestClient(app)
    
    # Create blueprint
    blueprint = {
        "schema_version": "1.1.0",
        "nodes": [{
            "id": "n1", 
            "type": "tool", 
            "tool_name": "sleep", 
            "tool_args": {"duration": 0.01},
            "input_schema": {"type": "object", "properties": {"duration": {"type": "number"}}},
            "output_schema": {"type": "object", "properties": {"success": {"type": "boolean"}}}
        }]
    }
    
    # Start multiple workflows
    run_ids = []
    for i in range(3):
        resp = client.post("/api/v1/mcp/runs", json={"blueprint": blueprint})
        run_ids.append(resp.json()["run_id"])
    
    # Wait for execution
    await asyncio.sleep(0.2)
    
    # Verify each workflow has its own event stream
    for run_id in run_ids:
        events = await redis_client.xread({f"run:{run_id}:events": "0"})
        assert len(events) > 0
        
        # Check for completion event
        stream_name, messages = events[0]
        last_event = json.loads(messages[-1][1]["data"])
        assert last_event["event"] == "workflow.completed" 