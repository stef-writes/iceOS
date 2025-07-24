import pytest

from ice_orchestrator.validation.schema_validator import SchemaValidator
from ice_core.models.node_models import ToolNodeConfig, LLMOperatorConfig, LLMConfig
from ice_core.models.enums import ModelProvider

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