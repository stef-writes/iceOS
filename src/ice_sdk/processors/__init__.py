"""Processor abstractions and runtime registry."""

from .base import Processor, ProcessorConfig
from ice_sdk.registry.operator import (
    OperatorRegistry as ProcessorRegistry,
    global_operator_registry as global_processor_registry,
)

__all__: list[str] = [
    "Processor",
    "ProcessorConfig",
    "ProcessorRegistry",
    "global_processor_registry",
]
