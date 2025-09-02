from __future__ import annotations

from pydantic import BaseModel

from ice_core.models.mcp import Blueprint
from ice_core.utils.node_conversion import convert_node_specs
from ice_core.validation.schema_validator import validate_blueprint


class GraphValidator(BaseModel):
    """Validate blueprints using core validators.

    - Enforces schema version and cycle checks via ``validate_blueprint``
    - Ensures runtime convertibility of node specs
    - Raises core domain exceptions on failure (callers should handle)
    """

    async def ensure_valid_async(self, blueprint: Blueprint) -> None:
        await validate_blueprint(blueprint)
        # Runtime conversion asserts material validity
        convert_node_specs(blueprint.nodes)

    # Remove sync wrapper to avoid event loop conflicts; callers should await ensure_valid_async
