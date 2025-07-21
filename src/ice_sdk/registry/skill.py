"""Shim exposing *SkillRegistry* under the new *ice_sdk.registry* package."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any

_impl: ModuleType = import_module("ice_sdk.skills.registry")

SkillRegistry: Any = getattr(_impl, "SkillRegistry")
global_skill_registry: Any = getattr(_impl, "global_skill_registry")
SkillRegistrationError: Any = getattr(_impl, "SkillRegistrationError")

__all__: list[str] = [
    "SkillRegistry",
    "global_skill_registry",
    "SkillRegistrationError",
]
