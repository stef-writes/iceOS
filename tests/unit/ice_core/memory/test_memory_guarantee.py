from ice_core.memory.memory_base_protocol import MemoryConfig
from ice_core.models.enums import MemoryGuarantee


def test_memory_guarantee_values():
    assert MemoryGuarantee.EPHEMERAL.value == "ephemeral"
    assert MemoryGuarantee.SHORT_TERM.value == "short_term"
    assert MemoryGuarantee.DURABLE.value == "durable"


def test_memory_config_accepts_guarantee():
    cfg = MemoryConfig(backend="memory", guarantee=MemoryGuarantee.EPHEMERAL)
    assert cfg.guarantee == MemoryGuarantee.EPHEMERAL


def test_memory_config_validation():
    cfg = MemoryConfig(backend="memory", guarantee=MemoryGuarantee.EPHEMERAL)
    # No exception expected
    from ice_core.memory.memory_base_protocol import (  # noqa: WPS433 – import for test
        BaseMemory,
    )

    class _DummyBackend(BaseMemory):
        async def initialize(self):
            pass

        async def store(self, key, content, metadata=None):
            pass

        async def retrieve(self, key):  # noqa: D401 – test stub
            return None

        async def search(self, query, limit=10, filters=None):
            return []

        async def delete(self, key):
            return False

        async def clear(self, pattern=None):
            return 0

        async def list_keys(self, pattern=None, limit=100):
            return []

    backend = _DummyBackend(cfg)
    backend.validate()  # Should not raise
