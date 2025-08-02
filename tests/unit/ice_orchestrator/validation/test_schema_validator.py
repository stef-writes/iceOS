import pytest

from ice_core.models.enums import ModelProvider
from ice_core.models.node_models import LLMConfig, LLMOperatorConfig, ToolNodeConfig
from ice_core.validation.schema_validator import SchemaValidator

pytestmark = [pytest.mark.unit]


def test_validator_raises_for_tool_without_schema() -> None:
    node = ToolNodeConfig(
        id="n1",
        type="tool",
        tool_name="dummy",
        input_schema={"a": "int"},
        output_schema={},
    )

    with pytest.raises(ValueError):
        SchemaValidator.is_output_valid(node, {})


def test_validator_ok_for_llm_without_schema() -> None:
    node = LLMOperatorConfig(
        id="n2",
        type="llm",
        model="gpt-4o",
        prompt="Hi",
        llm_config=LLMConfig(provider=ModelProvider.OPENAI),
        output_schema={},
    )

    # should not raise and return True
    assert SchemaValidator.is_output_valid(node, "hello") is True 