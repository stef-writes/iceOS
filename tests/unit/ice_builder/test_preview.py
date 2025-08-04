from __future__ import annotations

from ice_builder.dsl.workflow import WorkflowBuilder


def test_preview_mermaid() -> None:
    builder = WorkflowBuilder("preview_demo")
    builder.add_tool("node_a", tool_name="aggregator", results=[])
    builder.add_tool("node_b", tool_name="aggregator", results="{{ node_a }}")
    builder.connect("node_a", "node_b")

    diagram = builder.preview()
    # Basic sanity checks – contains node ids and arrow
    assert "node_a" in diagram and "node_b" in diagram and "-->" in diagram
