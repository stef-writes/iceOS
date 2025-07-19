from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel

from ice_sdk.utils.deprecation import deprecated

C = TypeVar("C", bound=BaseModel)

# ---------------------------------------------------------------------------
# Lightweight JSONSchema validation stub ------------------------------------
# ---------------------------------------------------------------------------


def validate_schemas(
    input_schema: Dict[str, Any], output_schema: Dict[str, Any]
) -> bool:  # noqa: D401
    """Return *True* when the provided JSON schemas have basic structure."""

    return isinstance(input_schema, dict) and isinstance(output_schema, dict)


class ProcessorConfig(BaseModel):
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    timeout: int = 30


@deprecated("0.4.0", "Use Processor instead")
class Node:  # noqa: D101 – legacy alias
    pass


class Processor(Generic[C]):
    """Base data transformation unit (generic over *config* type)."""

    config: C  # type: ignore[assignment]

    def validate(self) -> bool:  # noqa: D401
        return validate_schemas(self.config.input_schema, self.config.output_schema)  # type: ignore[attr-defined]

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        raise NotImplementedError
