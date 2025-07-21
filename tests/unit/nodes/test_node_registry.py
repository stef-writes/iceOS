import ice_orchestrator.execution.executors  # noqa: F401 – ensures registration side-effect
from ice_sdk.registry.node import get_executor


def test_builtin_executors_registered() -> None:
    """The built-in 'ai' and 'tool' executors should be available in the registry."""
    assert callable(get_executor("ai"))
    assert callable(get_executor("tool"))
