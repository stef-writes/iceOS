import pytest
from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def test_list_tools_endpoint():
    resp = client.get("/v1/tools")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_agents_units_chains_endpoints():
    for path in ("agents", "units", "chains"):
        resp = client.get(f"/v1/{path}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list) 