import pytest

from ice_core.exceptions import ValidationError
from ice_core.memory.base import MemoryConfig
from ice_core.memory.episodic import EpisodicMemory
from ice_core.memory.procedural import ProceduralMemory
from ice_core.memory.semantic import SemanticMemory
from ice_core.memory.working import WorkingMemory
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
