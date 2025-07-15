import pytest

from ice_orchestrator.errors.chain_errors import CircularDependencyError
from ice_orchestrator.graph.dependency_graph import DependencyGraph
from ice_sdk.models.node_models import ToolNodeConfig


class DummyNode(ToolNodeConfig):
    """Lightweight node subclass that allows easy instantiation."""

    class Config:
        arbitrary_types_allowed = True  # pragma: no cover


def _make_node(node_id: str, deps: list[str] | None = None) -> DummyNode:  # noqa: D401
    return DummyNode(
        id=node_id,
        name=node_id,
        tool_name="dummy",
        dependencies=deps or [],
    )


def test_level_assignment():
    """Nodes at depth 0/1/2 must be grouped correctly by DependencyGraph."""

    n1 = _make_node("root")
    n2 = _make_node("child1", ["root"])
    n3 = _make_node("child2", ["root"])
    n4 = _make_node("grand", ["child1"])

    dg = DependencyGraph([n1, n2, n3, n4])
    levels = dg.get_level_nodes()

    assert set(levels[0]) == {"root"}
    assert set(levels[1]) == {"child1", "child2"}
    assert set(levels[2]) == {"grand"}


def test_cycle_detection():
    """Graph with circular deps must raise CircularDependencyError."""

    a = _make_node("a", ["c"])
    b = _make_node("b", ["a"])
    c = _make_node("c", ["b"])

    with pytest.raises(CircularDependencyError):
        DependencyGraph([a, b, c])
