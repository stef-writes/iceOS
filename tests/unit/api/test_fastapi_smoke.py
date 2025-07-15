from typing import Generator

import pytest
from fastapi.testclient import TestClient

from ice_api.main import app


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Return a reusable FastAPI test client."""
    with TestClient(app) as _client:
        yield _client


def _assert_cors_headers(response):
    """Ensure CORS middleware is active on *response*."""
    assert response.headers.get("access-control-allow-origin") == "*"


class TestFastAPISmoke:
    """Basic availability checks for the public HTTP API."""

    def test_health_endpoint(self, client: TestClient):
        res = client.get("/health", headers={"Origin": "http://testclient"})
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}
        _assert_cors_headers(res)

    def test_tools_endpoint(self, client: TestClient):
        res = client.get("/v1/tools", headers={"Origin": "http://testclient"})
        assert res.status_code == 200
        # Should be JSON array of strings.
        data = res.json()
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data)
        _assert_cors_headers(res)

    def test_not_found(self, client: TestClient):
        res = client.get("/definitely/404", headers={"Origin": "http://testclient"})
        assert res.status_code == 404
        # Default JSON schema from FastAPI for 404s
        assert res.json()["detail"] == "Not Found"
        _assert_cors_headers(res)
