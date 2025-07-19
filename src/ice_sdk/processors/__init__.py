"""Processor abstractions and runtime registry."""

from .base import Processor, ProcessorConfig  # noqa: F401
from .registry import ProcessorRegistry, global_processor_registry  # noqa: F401

__all__: list[str] = [
    "Processor",
    "ProcessorConfig",
    "ProcessorRegistry",
    "global_processor_registry",
]
