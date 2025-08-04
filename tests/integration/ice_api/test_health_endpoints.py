import pytest
from fastapi.testclient import TestClient

from ice_api.main import app

client = TestClient(app)


def test_livez():
    resp = client.get("/livez")
    assert resp.status_code == 200
    assert resp.json()["status"] == "live"


def test_readyz():
    # READY_FLAG is set during lifespan startup in TestClient context
    resp = client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["status"] in {"ready", "starting"}