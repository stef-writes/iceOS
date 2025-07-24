import pytest
from fastapi.testclient import TestClient

from ice_api.main import app
from ice_sdk.services.initialization import initialize_services

# Initialize services before creating test client
initialize_services()

client = TestClient(app)


def test_list_tools_endpoint():
    resp = client.get("/api/v1/tools")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_agents_units_chains_endpoints():
    for path in ("agents", "units", "chains"):
        resp = client.get(f"/v1/{path}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list) 