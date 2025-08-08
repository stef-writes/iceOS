from typing import Any, Literal

from pydantic import BaseModel, Field


class EndpointSpec(BaseModel):
    method: Literal["POST", "GET"]
    path: str
    request_schema: dict[str, Any]  # JSON Schema
    response_schema: dict[str, Any]
    cost_weight: float = 1.0


class ServiceContract(BaseModel):
    """Defines a formal interface for cross-layer communication.

    Example:
        class ChainServiceContract(ServiceContract):
            get_chain: Callable[[str], ChainDefinition]
            register_chain: Callable[[ChainDefinition], str]

    Attributes:
        version (str): Semantic version of contract (major changes require new version)
        endpoints (dict[str, EndpointSpec]): Mapping of endpoint names to their specifications.
    """

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    endpoints: dict[str, EndpointSpec] = {}  # key = endpoint name
    schema_registry: dict[str, dict[str, Any]] = {}  # key = schema name
