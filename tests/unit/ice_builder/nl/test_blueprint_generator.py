from __future__ import annotations

from ice_builder.nl.generator import append_tool_node, create_partial_blueprint
from ice_core.base_tool import ToolBase


class EchoTool(ToolBase):
    name: ClassVar[str] = "echo"
    description: ClassVar[str] = "Echoes input"

    async def _execute_impl(self, text: str) -> dict[str, str]:
        return {"result": text}


# Register instance so generator can resolve it
_echo_instance = EchoTool()
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

registry.register_instance(NodeType.TOOL, "echo", _echo_instance, validate=False)  # type: ignore[arg-type]

def test_append_tool_node_injects_schema():
    bp = create_partial_blueprint("echo_test")
    append_tool_node(bp, node_id="n1", tool_name="echo")

    node = bp.nodes[0]

    # assert extra fields placed
    assert hasattr(node, "input_schema")
    assert node.input_schema["type"] == "object"  # type: ignore[index]
    assert hasattr(node, "progress_capable")
    assert node.progress_capable is False  # type: ignore[attr-defined]
