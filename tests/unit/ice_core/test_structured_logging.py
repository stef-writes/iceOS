import importlib
import json
import logging
import os
from types import ModuleType

import pytest


@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    """Ensure JSON logging is enabled to stdout for this test."""
    monkeypatch.setenv("ICE_LOG_JSON", "stdout")
    # Reduce noise from other env variables that could affect output
    monkeypatch.delenv("ICE_ENV", raising=False)
    yield
    monkeypatch.delenv("ICE_LOG_JSON", raising=False)


def _reload_logging_module() -> ModuleType:
    """Reload the logger module after env tweak so setup runs again."""
    # Clear existing handlers to avoid duplicate emission
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    import importlib
    return importlib.reload(importlib.import_module("ice_core.utils.logging"))


def test_json_log_line_contains_expected_keys(capsys):
    mod = _reload_logging_module()
    logger = mod.setup_logger()
    logger.info("hello structured")

    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)

    assert data["message"] == "hello structured"
    assert data["level"] == "INFO"
    assert "timestamp" in data
    # Trace fields should exist even if None
    assert "trace_id" in data
    assert "span_id" in data
