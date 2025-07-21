from __future__ import annotations

from ..utils.errors import SkillExecutionError
from .base import SkillBase, ToolContext, function_tool
from .registry import SkillRegistry, global_skill_registry

# Domain skills -------------------------------------------------------------
from .web.search_skill import WebSearchSkill  # – default registration

# ---------------------------------------------------------------------------
# Default skill registrations – executed on package import -------------------
# ---------------------------------------------------------------------------
try:
    global_skill_registry.register("web_search", WebSearchSkill())
except Exception:  # pragma: no cover
    # Registration failures should not break import; logged by registry.
    pass

# ---------------------------------------------------------------------------
# Public re-exports (v2 names only) -----------------------------------------
# ---------------------------------------------------------------------------

# Expose the key helper types directly on the *skills* package so that tests
# can import ``from ice_sdk.skills import SkillBase, function_tool`` without
# relying on the legacy *tools* namespace.

SkillBase = SkillBase  # type: ignore[assignment]
SkillExecutionError = SkillExecutionError  # type: ignore[assignment]
ToolContext = ToolContext  # type: ignore[assignment]
function_tool = function_tool  # type: ignore[assignment]

# Public API surface ---------------------------------------------------------

__all__: list[str] = [
    "SkillBase",
    "SkillExecutionError",
    "ToolContext",
    "function_tool",
    "SkillRegistry",
    "global_skill_registry",
]
