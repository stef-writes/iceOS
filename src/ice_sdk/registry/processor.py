"""Shim exposing *ProcessorRegistry* under the new unified path."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any

_impl: ModuleType = import_module("ice_sdk.processors.registry")

ProcessorRegistry: Any = getattr(_impl, "ProcessorRegistry")
global_processor_registry: Any = getattr(_impl, "global_processor_registry")

__all__: list[str] = [
    "ProcessorRegistry",
    "global_processor_registry",
]
