import sys
import types
from typing import Dict, Any

import pytest

from ice_core.models.node_models import PrebuiltAgentConfig
from ice_sdk.registry.node import get_executor

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


_install_dummy_module("dummy_agents.good", _GoodAgent)
_install_dummy_module("dummy_agents.bad", _BadAgent)


@pytest.mark.asyncio
async def test_agent_executor_success() -> None:
    cfg = PrebuiltAgentConfig(
        id="good",
        package="dummy_agents.good",
        agent_attr="_GoodAgent",
        agent_config={"ping": "pong"},
    )
    executor = get_executor("agent")
    result = await executor(None, cfg, {"msg": "hi"})  # type: ignore[arg-type]
    assert result.success is True
    assert result.output == {"echo": "hi"}


@pytest.mark.asyncio
async def test_agent_executor_failure_missing_execute() -> None:
    cfg = PrebuiltAgentConfig(
        id="bad",
        package="dummy_agents.bad",
        agent_attr="_BadAgent",
    )
    executor = get_executor("agent")
    result = await executor(None, cfg, {})  # type: ignore[arg-type]
    assert result.success is False
    assert "execute" in (result.error or "") 