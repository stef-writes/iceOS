from __future__ import annotations

from typing import Any

import pytest
from opentelemetry import trace

# Pre-import modules required for tests --------------------------------
from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.tools.base import BaseTool

# Skip if opentelemetry SDK missing -----------------------------------
otlp = pytest.importorskip("opentelemetry.sdk")

# Attempt to import SDK classes – skip test if unavailable (optional dependency)
try:
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore  # noqa: F401
    from opentelemetry.sdk.trace.export import (  # type: ignore  # noqa: F401
        InMemorySpanExporter,
        SimpleSpanProcessor,
    )
except Exception:  # pragma: no cover – let pytest handle skip
    pytest.skip(
        "OpenTelemetry SDK with InMemorySpanExporter unavailable",
        allow_module_level=True,
    )


class DummyTool(BaseTool):
    name = "dummy_span"
    description = "Returns OK"

    async def run(self, **kwargs: Any):  # type: ignore[override]
        return {"ok": True}


@pytest.mark.asyncio
async def test_node_execute_span_emitted():
    # Configure in-memory exporter ----------------------------------------
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    node_cfg = ToolNodeConfig(id="t1", name="Dummy", tool_name="dummy_span")
    chain = ScriptChain(nodes=[node_cfg], tools=[DummyTool()], name="span-test")

    result = await chain.execute()
    assert result.success is True

    spans = exporter.get_finished_spans()
    # Ensure at least one node.execute span exists ------------------------
    assert any(span.name == "node.execute" for span in spans)
