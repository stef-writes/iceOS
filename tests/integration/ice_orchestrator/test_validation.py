import asyncio

import pytest

from ice_core.models.mcp import Blueprint, NodeSpec
from ice_orchestrator.validation.schema_validator import (
    CircularDependencyError,
    InvalidSchemaVersionError,
    validate_blueprint,
)


# Helper NodeSpec for reuse ---------------------------------------------------
_valid_node = NodeSpec(id="n1", type="tool")


@pytest.mark.asyncio
async def test_circular_detection() -> None:
    """Blueprints with cycles must raise ``CircularDependencyError``."""

    nodes = [
        NodeSpec(id="a", type="tool", dependencies=["b"]),
        NodeSpec(id="b", type="tool", dependencies=["a"]),
    ]

    with pytest.raises(CircularDependencyError):
        await validate_blueprint(Blueprint(nodes=nodes, schema_version="1.1.0"))


@pytest.mark.asyncio
async def test_schema_version_enforcement() -> None:
    """Unsupported schema version must raise ``InvalidSchemaVersionError``."""

    bp = Blueprint(nodes=[_valid_node], schema_version="2.0.0")

    with pytest.raises(InvalidSchemaVersionError):
        await validate_blueprint(bp)