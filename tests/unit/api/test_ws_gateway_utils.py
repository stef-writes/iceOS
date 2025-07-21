"""Unit tests for internal helpers in ws_gateway (auth & schema validators)."""

from __future__ import annotations

import pytest
from fastapi import WebSocketDisconnect
from ice_api.ws_gateway import _SCHEMAS, _VALIDATORS, _assert_auth, _auth_token


class _StubWS:  # noqa: D401 – simple stub
    def __init__(self, proto: str):
        self.headers = {"sec-websocket-protocol": proto}


def test_auth_token_env(monkeypatch) -> None:  # noqa: D103
    monkeypatch.setenv("ICE_WS_BEARER", "sec123")
    assert _auth_token() == "sec123"


def test_assert_auth_pass(monkeypatch):  # noqa: D103
    monkeypatch.setenv("ICE_WS_BEARER", "token1")
    ws = _StubWS(proto="token1")
    # Does not raise
    _assert_auth(ws)


def test_assert_auth_fail(monkeypatch):  # noqa: D103
    monkeypatch.setenv("ICE_WS_BEARER", "good")
    ws = _StubWS(proto="bad")
    with pytest.raises(WebSocketDisconnect):
        _assert_auth(ws)


@pytest.mark.parametrize("name", list(_SCHEMAS.keys()))
def test_schema_validators_accept_valid(name):  # noqa: D103
    # Build a minimal valid message for each schema -------------------------
    if name == "patch_node":
        msg = {"t": "patch_node", "node_id": "n1", "field": "name", "value": 42}
    elif name == "telemetry":
        msg = {"t": "telemetry", "node_id": "n1", "latency_ms": 5.5, "cost": 0.01}
    else:  # cursor
        msg = {"t": "cursor", "user": "alice", "x": 10, "y": 20}

    _VALIDATORS[name].validate(msg)  # should not raise


@pytest.mark.parametrize("name", list(_SCHEMAS.keys()))
def test_schema_validators_reject_missing_field(name):  # noqa: D103
    # Start from a valid message and delete one required key ---------------
    if name == "patch_node":
        msg = {"t": "patch_node", "node_id": "n1", "field": "name"}  # missing "value"
    elif name == "telemetry":
        msg = {"t": "telemetry", "node_id": "n1", "latency_ms": 5.5}  # missing cost
    else:  # cursor
        msg = {"t": "cursor", "user": "bob", "x": 1}  # missing y

    with pytest.raises(Exception):
        _VALIDATORS[name].validate(msg)
