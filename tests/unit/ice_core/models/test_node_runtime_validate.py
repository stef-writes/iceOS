import pytest

from ice_core.models.node_models import LLMOperatorConfig, SkillNodeConfig, LLMConfig
from ice_core.models.enums import ModelProvider

pytestmark = [pytest.mark.unit]


def test_llm_node_auto_output_schema():
    cfg = LLMOperatorConfig(
        id="ai1",
        type="llm",
        model="gpt-4o",
        prompt="hello",
        llm_config=LLMConfig(provider=ModelProvider.OPENAI),
    )
    # Should not raise and should set default output_schema
    cfg.runtime_validate()
    assert cfg.output_schema == {"text": "string"}


def test_tool_node_missing_schema_raises():
    cfg = SkillNodeConfig(
        id="t1",
        type="tool",
        tool_name="noop",
        tool_args={},
        input_schema={},
        output_schema={},
    )
    with pytest.raises(ValueError):
        cfg.runtime_validate() 