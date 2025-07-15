import pytest

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.models.node_models import ToolNodeConfig
from ice_sdk.orchestrator.base_script_chain import FailurePolicy


class FailingNode(ToolNodeConfig):
    class Config:
        arbitrary_types_allowed = True

    def runtime_validate(self) -> None:  # type: ignore[override]
        raise ValueError("forced validation error")


@pytest.mark.asyncio
async def test_runtime_validate_failure():
    n1 = FailingNode(id="bad", name="bad", tool_name="dummy", dependencies=[])

    chain = ScriptChain(
        nodes=[n1],
        name="validate-test",
        failure_policy=FailurePolicy.CONTINUE_POSSIBLE,
        validate_outputs=False,
        use_cache=False,
    )

    async def _dummy(*args, **kwargs):
        return {"ok": True}

    original_execute_tool = chain.context_manager.execute_tool  # type: ignore[assignment]

    chain.context_manager.execute_tool = _dummy  # type: ignore[assignment]

    result = await chain.execute()

    # Restore original method so other tests are unaffected
    chain.context_manager.execute_tool = original_execute_tool  # type: ignore[assignment]

    assert result.success is False
    assert "validation error" in (result.error or "")
