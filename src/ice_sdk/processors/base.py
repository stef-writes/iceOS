from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel

from ice_sdk.utils.deprecation import deprecated

C = TypeVar("C", bound=BaseModel)

# ---------------------------------------------------------------------------
# Lightweight JSONSchema validation stub ------------------------------------
# ---------------------------------------------------------------------------


def validate_schemas(
    input_schema: Dict[str, Any], output_schema: Dict[str, Any]
) -> bool:
    """Return *True* when the provided JSON schemas have basic structure."""

    return isinstance(input_schema, dict) and isinstance(output_schema, dict)


class ProcessorConfig(BaseModel):
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    timeout: int = 30


@deprecated("0.4.0", "Use Processor instead")
class Node:  # – legacy alias
    pass


class Processor(Generic[C]):
    """Base data transformation unit (generic over *config* type).

    Subclasses **must** override the class attribute ``name`` with a stable
    identifier used for registry look-up.  A default empty string prevents
    attribute-access errors during registration while still triggering
    validation in :pymeth:`ProcessorRegistry.register`.
    """

    # Public identifier — overridden by concrete processors -----------------
    name: str = ""

    # Concrete configuration instance supplied by subclasses or dynamically
    # injected by orchestration layers (e.g. CLI).  We only declare the
    # attribute so that static type checkers recognise its existence.
    config: C  # type: ignore[assignment]

    def validate(self) -> bool:
        return validate_schemas(self.config.input_schema, self.config.output_schema)  # type: ignore[attr-defined]

    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
