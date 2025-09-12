from __future__ import annotations

import sys
import types
from typing import Any, Dict

import pytest

from ice_core.models.node_models import CodeNodeConfig
from ice_core.unified_registry import register_code_factory
from ice_orchestrator.execution.executors.builtin.code_node_executor import (
    code_node_executor,
)


class _DummyWorkflow:
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no cover
        return {}


def _register_dynamic_code_factory(name: str, fn_name: str = "create") -> None:
    mod_name = f"dyn_test_code_{name}"
    module = types.ModuleType(mod_name)

    def create(**kwargs: Any) -> Dict[str, Any]:  # type: ignore[no-redef]
        # Attempt a network call which should be blocked by the executor policy
        import socket  # noqa: WPS433 (test-only)

        try:
            socket.create_connection(("example.com", 80), timeout=0.5)
        except Exception as e:  # network should be disabled
            return {"result": f"blocked:{type(e).__name__}"}
        return {"result": "unexpected-net-allowed"}

    setattr(module, fn_name, create)
    sys.modules[mod_name] = module
    register_code_factory(name, f"{mod_name}:{fn_name}")


@pytest.mark.asyncio
async def test_code_node_executor_blocks_network_and_validates_output() -> None:
    factory_name = "test_math_code"
    _register_dynamic_code_factory(factory_name)

    cfg = CodeNodeConfig(
        id="n1",
        type="code",
        name=factory_name,
        language="python",
        # Require explicit schemas (hardened)
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        sandbox=True,
        imports=[],
    )

    ctx: Dict[str, Any] = {"org_id": "org_test"}
    res = await code_node_executor(_DummyWorkflow(), cfg, ctx)

    assert res.metadata.node_id == "n1"
    assert res.success is True
    # The factory attempted a socket connection; executor policy should block it
    assert isinstance(res.output, dict)
    assert res.output.get("result", "").startswith("blocked:")

