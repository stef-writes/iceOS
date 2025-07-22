from __future__ import annotations

"""Tool registry – canonical home for deterministic tool implementations.

Wraps the existing *SkillRegistry* but with taxonomy-aligned naming.  Future
code should import *ToolRegistry* / *global_tool_registry*.
"""

import warnings
from typing import Any

from ice_sdk.tools.registry import SkillRegistry as _SkillRegistry

__all__: list[str] = [
    "ToolRegistry",
    "global_tool_registry",
]


class ToolRegistry(_SkillRegistry):
    """Alias for existing SkillRegistry – semantic rename only."""

    pass


global_tool_registry: "ToolRegistry[Any]" = ToolRegistry()  # type: ignore[type-var]

warnings.warn(
    "'global_skill_registry' is deprecated; use 'global_tool_registry' from 'ice_sdk.registry.tool'.",
    DeprecationWarning,
    stacklevel=2,
) 