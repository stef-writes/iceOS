from ice_sdk.context.manager import GraphContextManager
from ice_sdk.context.memory import NullMemory


def test_null_memory_usage():
    """GraphContextManager should allow injection of a custom memory adapter.

    The *NullMemory* adapter is expected to silently discard any stored
    vectors and always return an empty recall result.
    """
    manager = GraphContextManager(memory=NullMemory())  # Dependency injection

    # These synchronous helpers should be no-ops but still callable.
    manager.memory.store("test", [0.1, 0.2, 0.3])  # type: ignore[arg-type]
    assert manager.memory.recall([0.1, 0.2]) == []
