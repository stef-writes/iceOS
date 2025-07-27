import pytest

from ice_core.models.mcp import NodeSpec
from ice_core.utils.node_conversion import convert_node_spec

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ("node_type", "extra"),
    [
        (
            "tool",
            {"tool_name": "echo"},
        ),
        (
            "llm",
            {
                "model": "gpt-3.5-turbo",
                "prompt": "Say hello",
                "llm_config": {"provider": "openai"},
            },
        ),
        (
            "agent",
            {"package": "dummy.package"},
        ),
        (
            "condition",
            {"expression": "True"},
        ),
        (
            "workflow",
            {"workflow_ref": "dummy"},
        ),
        (
            "loop",
            {"items_source": "data.items", "body_nodes": ["node1"], "max_iterations": 10},
        ),
        (
            "parallel",
            {"branches": [["node1"], ["node2"]]},
        ),
        (
            "code",
            {"code": "output['result'] = 42", "language": "python"},
        ),
    ],
)
def test_convert_node_spec_accepts_canonical_types(node_type: str, extra: dict) -> None:
    spec = NodeSpec(id="n1", type=node_type, **extra)
    cfg = convert_node_spec(spec)
    assert cfg.type == node_type


@pytest.mark.parametrize(
    "node_type",
    [
        "ai",
        "tool",
        "prebuilt",
        "subdag",
    ],
)
def test_convert_node_spec_rejects_legacy_aliases(node_type: str) -> None:
    spec = NodeSpec(id="n_bad", type=node_type)
    with pytest.raises(ValueError):
        convert_node_spec(spec) 