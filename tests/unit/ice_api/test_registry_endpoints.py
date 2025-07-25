import pytest
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.initialization import initialize_services
from ice_sdk.services.locator import ServiceLocator
from ice_sdk.tools.service import ToolService

# Initialize services before creating test client
initialize_services()

# Ensure ToolService is registered
if not ServiceLocator.get("tool_service"):
    ServiceLocator.register("tool_service", ToolService())

client = TestClient(app)


def test_list_tools_endpoint():
    resp = client.get("/api/v1/tools")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    # The list might be empty in test environment, that's ok
    # Just ensure it returns a list


def test_list_agents_units_chains_endpoints():
    for path in ("agents", "units", "chains"):
        resp = client.get(f"/v1/{path}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        # The lists might be empty in test environment, that's ok 