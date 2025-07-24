import pytest

from ice_orchestrator.validation.schema_validator import SchemaValidator
from ice_core.models.node_models import ToolNodeConfig

pytestmark = [pytest.mark.unit]


def test_schema_validator_output_match():
    node = ToolNodeConfig(
        id="n1",
        type="tool",
        tool_name="noop",
        tool_args={},
        input_schema={"a": "int"},
        output_schema={"msg": "str", "count": "int"},
    )
    output = {"msg": "hi", "count": 5}
    assert SchemaValidator.is_output_valid(node, output) is True


def test_schema_validator_output_mismatch():
    node = ToolNodeConfig(
        id="n2",
        type="tool",
        tool_name="noop",
        tool_args={},
        input_schema={"a": "int"},
        output_schema={"msg": "str", "count": "int"},
    )
    bad_output = {"msg": 123, "count": "five"}
    assert SchemaValidator.is_output_valid(node, bad_output) is False 