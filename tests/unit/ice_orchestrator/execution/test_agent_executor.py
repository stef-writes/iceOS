import sys
import types
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

import pytest

from ice_core.models.node_models import AgentNodeConfig
from ice_sdk.registry.node import get_executor
from ice_sdk.unified_registry import registry
from ice_core.models import NodeType

# Import executors to ensure they're registered
import ice_orchestrator.execution.executors.unified  # noqa: F401

# Mark as unit so we can filter via -m "unit"
pytestmark = [pytest.mark.unit]

# ---------------------------------------------------------------------------
# Helpers – dynamic dummy agent modules -------------------------------------
# ---------------------------------------------------------------------------

def _install_dummy_module(name: str, cls):  # noqa: ANN001
    mod = types.ModuleType(name)
    setattr(mod, cls.__name__, cls)
    sys.modules[name] = mod


# Valid agent with validate + async execute ----------------------------------
class _GoodAgent:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def validate(self) -> None:  # noqa: D401
        if "ping" not in self.kwargs:
            raise ValueError("ping key required")

    async def execute(self, ctx: Dict[str, Any]):  # noqa: D401, ANN001
        return {"echo": ctx.get("msg", "")}


# Invalid agent (no execute) --------------------------------------------------
class _BadAgent:
    def validate(self) -> None:  # noqa: D401
        pass


# Create mock agents for testing
good_agent_mock = Mock()
good_agent_mock.execute = AsyncMock(return_value={"echo": "hi"})

bad_agent_mock = Mock()
# No execute method on bad agent

# Register the agents so the executor can find them
registry.register_instance(NodeType.AGENT, "good_agent", good_agent_mock)
registry.register_instance(NodeType.AGENT, "bad_agent", bad_agent_mock)


@pytest.mark.asyncio
async def test_agent_executor_success() -> None:
    cfg = AgentNodeConfig(
        id="good",
        package="good_agent",  # Use the registry key
        type="agent"
    )
    executor = get_executor("agent")
    result = await executor(None, cfg, {"msg": "hi"})  # type: ignore[arg-type]
    assert result.success is True
    assert result.output == {"echo": "hi"}


@pytest.mark.asyncio
async def test_agent_executor_failure_missing_execute() -> None:
    cfg = AgentNodeConfig(
        id="bad",
        package="bad_agent",  # Use the registry key
        type="agent"
    )
    executor = get_executor("agent")
    result = await executor(None, cfg, {})  # type: ignore[arg-type]
    assert result.success is False
    assert "'Mock' object has no attribute 'execute'" in (result.error or "") or "execute" in (result.error or "") 