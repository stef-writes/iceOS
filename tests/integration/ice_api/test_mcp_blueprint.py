"""Integration tests for MCP blueprint API endpoints using real Redis."""

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.locator import ServiceLocator


pytestmark = [pytest.mark.integration]


class _StubWorkflowService:  # pylint: disable=too-few-public-methods
    async def execute(  # noqa: D401
        self,
        nodes: list[Any],  # noqa: ANN401 – runtime list
        name: str,
        max_parallel: int = 5,
        *,
        run_id: str | None = None,  # noqa: D401 – keep signature identical
        event_emitter=None,  # noqa: ANN401
    ) -> Dict[str, Any]:
        # Emit a dummy event to simulate node completion
        if event_emitter is not None:
            event_emitter("workflow.node", {"msg": "done"})
        return {"success": True, "output": {"hello": "world"}}


@pytest.fixture(autouse=True)
def setup_test_env(redis_url: str):
    """Set up test environment with Redis URL and stub workflow service."""
    import os
    os.environ["REDIS_URL"] = redis_url
    
    # Register stub workflow service
    ServiceLocator.register("workflow_service", _StubWorkflowService())
    
    yield
    
    # Cleanup
    ServiceLocator.clear()


def _build_minimal_llm_blueprint() -> Dict[str, Any]:
    """Return a minimal, valid blueprint payload as plain dict."""
    node = {
        "id": "n1",
        "type": "llm",
        "model": "gpt-4o",
        "prompt": "Say hi",
        "llm_config": {"provider": "openai"},
    }
    return {"schema_version": "1.1.0", "nodes": [node]}


@pytest.mark.asyncio
async def test_blueprint_registration_success(redis_client) -> None:
    """Test successful blueprint registration with real Redis."""
    client = TestClient(app)
    
    payload = _build_minimal_llm_blueprint()
    resp = client.post("/api/v1/mcp/blueprints", json=payload)

    assert resp.status_code == 201, resp.json()
    body = resp.json()
    assert body.get("status") == "accepted"
    assert "blueprint_id" in body
    
    # Verify blueprint is stored in Redis
    blueprint_id = body["blueprint_id"]
    stored = await redis_client.hget(f"blueprint:{blueprint_id}", "data")
    assert stored is not None


@pytest.mark.integration
def test_blueprint_registration_invalid() -> None:
    """Test invalid blueprint registration."""
    client = TestClient(app)
    
    # Missing required fields for deterministic tool node → 400
    invalid_node = {"id": "n1", "type": "tool"}
    resp = client.post("/api/v1/mcp/blueprints", json={"nodes": [invalid_node]})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_blueprint_retrieval(redis_client) -> None:
    """Test blueprint retrieval after registration."""
    client = TestClient(app)
    
    # Register blueprint
    payload = _build_minimal_llm_blueprint()
    resp = client.post("/api/v1/mcp/blueprints", json=payload)
    blueprint_id = resp.json()["blueprint_id"]
    
    # Retrieve blueprint
    get_resp = client.get(f"/api/v1/mcp/blueprints/{blueprint_id}")
    assert get_resp.status_code == 200
    
    # Verify content matches
    retrieved = get_resp.json()
    assert retrieved["nodes"][0]["id"] == "n1"
    assert retrieved["nodes"][0]["prompt"] == "Say hi" 