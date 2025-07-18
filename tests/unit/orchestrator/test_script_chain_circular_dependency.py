import pytest

from ice_orchestrator.errors.chain_errors import CircularDependencyError
from ice_orchestrator.workflow import ScriptChain
from ice_sdk.models.node_models import SkillNodeConfig


def _make_tool_node(node_id: str, deps: list[str] | None = None) -> SkillNodeConfig:
    return SkillNodeConfig(
        id=node_id,
        name=f"Node {node_id}",
        tool_name="dummy_tool",
        tool_args={},
        dependencies=deps or [],
    )


def test_circular_dependency_detection():
    # Create three nodes with a dependency loop A -> B -> C -> A
    node_a = _make_tool_node("A", deps=["C"])
    node_b = _make_tool_node("B", deps=["A"])
    node_c = _make_tool_node("C", deps=["B"])

    with pytest.raises(CircularDependencyError) as exc_info:
        _ = ScriptChain(nodes=[node_a, node_b, node_c])

    # Error message should list the offending node ids
    msg = str(exc_info.value)
    for nid in ("A", "B", "C"):
        assert nid in msg
