"""Tests for agent registry symmetry helpers."""
import sys
from types import ModuleType

import pytest

from ice_core.unified_registry import registry


class _DummyAgent:  # noqa: D101 – minimal stub
    pass


def _inject_dummy_module() -> str:  # helper to create module at runtime
    module_name = "_dummy_agent_mod"
    mod = ModuleType(module_name)
    mod.DummyAgent = _DummyAgent  # type: ignore[attr-defined]
    sys.modules[module_name] = mod
    return f"{module_name}:DummyAgent"


def test_agent_registration_and_lookup():
    """Registry should return correct class and list all agents."""
    import_path = _inject_dummy_module()

    # Register agent
    registry.register_agent("dummy", import_path)

    # list_agents symmetry
    agents = registry.list_agents()
    assert "dummy" in agents

    # get_agent_class symmetry
    agent_cls = registry.get_agent_class("dummy")
    assert agent_cls is _DummyAgent

    # idempotent lookup – second call should use cache
    agent_cls_cached = registry.get_agent_class("dummy")
    assert agent_cls_cached is _DummyAgent


if __name__ == "__main__":
    pytest.main([__file__])
