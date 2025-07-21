"""Processor abstractions and runtime registry."""

from .base import Processor, ProcessorConfig
from .registry import ProcessorRegistry, global_processor_registry

__all__: list[str] = [
    "Processor",
    "ProcessorConfig",
    "ProcessorRegistry",
    "global_processor_registry",
]
