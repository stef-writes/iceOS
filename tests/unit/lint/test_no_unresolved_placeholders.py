import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import AiNodeConfig


@pytest.mark.asyncio
async def test_prompt_placeholder_validation():
    """Chain execution should fail when prompt placeholders are unresolved."""

    node = AiNodeConfig(
        id="ai1",
        name="AI1",
        type="ai",
        model="gpt-3.5-turbo",
        prompt="Hello {missing}",  # unresolved placeholder
        llm_config={},  # type: ignore[arg-type]
        dependencies=[],
    )

    chain = ScriptChain(
        nodes=[node],
        name="invalid",
        persist_intermediate_outputs=False,
        use_cache=False,
    )

    result = await chain.execute()

    assert result.success is False
    assert result.error is not None
