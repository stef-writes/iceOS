from pydantic import BaseModel, Field
from typing import Literal

class EndpointSpec(BaseModel):
    method: Literal["POST", "GET"]
    path: str
    request_schema: dict  # JSON Schema
    response_schema: dict
    cost_weight: float = 1.0

class ServiceContract(BaseModel):
    """Versioned API contract between services"""
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    endpoints: dict[str, EndpointSpec] = {}  # key = endpoint name
    schema_registry: dict[str, dict] = {}  # key = schema name 