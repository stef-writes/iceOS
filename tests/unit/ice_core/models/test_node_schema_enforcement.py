import pytest

from ice_core.models.node_models import (
    ToolNodeConfig,
    LLMOperatorConfig,
    LLMConfig,
)
from ice_core.models.enums import ModelProvider

pytestmark = [pytest.mark.unit]


def test_tool_without_schema_raises() -> None:
    cfg = ToolNodeConfig(
        id="t1",
        type="tool",
        tool_name="dummy",
        input_schema={},
        output_schema={},
    )

    with pytest.raises(ValueError):
        cfg.runtime_validate()


def test_llm_without_output_schema_defaults() -> None:
    cfg = LLMOperatorConfig(
        id="llm1",
        type="llm",
        model="gpt-4o",
        prompt="Hi",
        llm_config=LLMConfig(provider=ModelProvider.OPENAI),
        input_schema={},
        output_schema={},
    )

    # Should not raise and should set default
    cfg.runtime_validate()
    assert cfg.output_schema == {"text": "string"} 