import json
import os

import httpx


def _base() -> str:
    return os.environ.get("ICE_API_URL", "http://localhost:8000")


def _headers() -> dict[str, str]:
    token = os.environ.get("ICE_API_TOKEN", "dev-token")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


import pytest


@pytest.mark.integration
def test_builder_suggest_smoke(monkeypatch) -> None:
    # Enable prompt planner for this test (no guarantee LLM key exists, so planner may return empty)
    monkeypatch.setenv("ICE_BUILDER_USE_PROMPT_PLANNER", "1")
    monkeypatch.setenv("ICE_BUILDER_USE_REGISTRY_CONTEXT", "1")

    payload = {"text": "add a tool node to parse CSV", "canvas_state": {}}

    with httpx.Client(timeout=10.0) as c:
        r = c.post(
            f"{_base()}/api/v1/builder/suggest", headers=_headers(), json=payload
        )
        r.raise_for_status()
        data = r.json()
        assert "patches" in data
        assert isinstance(data["patches"], list)
        # Planner may return [] if no LLM key; shape must still be correct


@pytest.mark.integration
def test_builder_apply_noop(monkeypatch) -> None:
    monkeypatch.setenv("ICE_BUILDER_USE_PROMPT_PLANNER", "0")  # deterministic
    pb = {"schema_version": "1.1.0", "nodes": []}
    payload = {"blueprint": pb, "patches": []}

    with httpx.Client(timeout=10.0) as c:
        r = c.post(f"{_base()}/api/v1/builder/apply", headers=_headers(), json=payload)
        r.raise_for_status()
        data = r.json()
        assert "blueprint" in data
        assert data["blueprint"]["schema_version"].startswith("1.")
