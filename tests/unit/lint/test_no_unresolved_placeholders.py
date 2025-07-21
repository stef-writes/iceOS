import pytest
from ice_core.models.model_registry import get_default_model_id

from ice_orchestrator.workflow import Workflow
from ice_sdk.models.node_models import LLMOperatorConfig


@pytest.mark.asyncio
async def test_prompt_placeholder_validation():
    """Chain execution should fail when prompt placeholders are unresolved."""

    node = LLMOperatorConfig(
        id="ai1",
        name="AI1",
        type="ai",
        model=get_default_model_id(),
        prompt="Hello {missing}",  # unresolved placeholder
        llm_config={},  # type: ignore[arg-type]
        dependencies=[],
    )

    chain = Workflow(
        nodes=[node],
        name="invalid",
        persist_intermediate_outputs=False,
        use_cache=False,
    )

    result = await chain.execute()

    assert result.success is False
    assert result.error is not None
