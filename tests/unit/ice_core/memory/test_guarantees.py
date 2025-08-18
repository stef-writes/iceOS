import pytest

from ice_core.exceptions import ValidationError
from ice_core.memory.episodic_memory_store import EpisodicMemory
from ice_core.memory.memory_base_protocol import MemoryConfig
from ice_core.memory.procedural_memory_store import ProceduralMemory
from ice_core.memory.semantic_memory_store import SemanticMemory
from ice_core.memory.working_memory_store import WorkingMemory
from ice_core.models.enums import MemoryGuarantee


@pytest.mark.parametrize(
    "cls, expected",
    [
        (WorkingMemory, {MemoryGuarantee.EPHEMERAL}),
        (EpisodicMemory, {MemoryGuarantee.TTL}),
        (ProceduralMemory, {MemoryGuarantee.DURABLE}),
        (SemanticMemory, {MemoryGuarantee.DURABLE, MemoryGuarantee.VECTORISED}),
    ],
)
async def test_guarantees_match_default(cls, expected):  # type: ignore[func-name-mismatch]
    mem = cls(MemoryConfig(enable_vector_search=True))  # type: ignore[arg-type]
    assert mem.guarantees() == expected


def test_validation_failure():
    """Requesting stronger guarantee than offered should raise."""
    cfg = MemoryConfig(backend="memory", guarantee=MemoryGuarantee.DURABLE)
    mem = WorkingMemory(cfg)
    with pytest.raises(ValidationError):
        mem.validate()
