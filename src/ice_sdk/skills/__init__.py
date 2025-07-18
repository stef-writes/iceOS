from __future__ import annotations

from .registry import SkillRegistry, global_skill_registry  # noqa: F401
from .base import SkillBase  # noqa: F401
from ..utils.errors import SkillExecutionError  # noqa: F401

# ---------------------------------------------------------------------------
# Default skill registrations – executed on package import -------------------
# ---------------------------------------------------------------------------
try:
    global_skill_registry.register("web_search", WebSearchSkill())
except Exception:  # pragma: no cover
    # Registration failures should not break import; logged by registry.
    pass 

# ---------------------------------------------------------------------------
# Legacy module alias – so that ``import ice_sdk.tools.base`` keeps working.
# ---------------------------------------------------------------------------
import sys
import types

from .base import ToolContext, function_tool, SkillBase

_legacy_module = types.ModuleType("ice_sdk.tools.base")
_legacy_module.ToolContext = ToolContext
_legacy_module.function_tool = function_tool
_legacy_module.SkillBase = SkillBase
_legacy_module.SkillBase = SkillBase  # alias for historic name
_legacy_module.SkillExecutionError = SkillExecutionError  # compatibility shim
sys.modules["ice_sdk.tools.base"] = _legacy_module 

# ---------------------------------------------------------------------------
# Legacy *package* alias – ``ice_sdk.tools`` + selected submodules ----------
# ---------------------------------------------------------------------------
# Many tests and user workflows still import helper utilities from the old
# ``ice_sdk.tools`` namespace.  We dynamically create a lightweight module
# hierarchy that forwards to the new *Skill* abstractions.  This makes Phase 0
# completely non-breaking while guiding users towards the v2 vocabulary.

import asyncio
import inspect
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel


# Root package --------------------------------------------------------------
tools_pkg = ModuleType("ice_sdk.tools")
# Expose submodule objects as attributes so ``import ice_sdk.tools.service``
# and ``from ice_sdk.tools import service`` both work.
tools_pkg.base = _legacy_module  # type: ignore[attr-defined]
sys.modules["ice_sdk.tools"] = tools_pkg

# ------------------------------------------------------------------
# tools.service – thin compatibility wrapper around new *Skill* layer
# ------------------------------------------------------------------

service_mod = ModuleType("ice_sdk.tools.service")


class ToolRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """Minimal wrapper forwarded to ToolService.execute()."""

    tool_name: str
    inputs: dict  # noqa: D401 – generic mapping
    context: dict


class ToolService:  # noqa: D401 – thin shim for backwards-compat
    """Compatibility facade mapping to *Skill* implementations.

    The implementation purposefully stays *minimal*.  It supports only the
    subset required by the existing unit-tests and orchestrator runtime:

        • ``register(cls)`` – register *Skill* class
        • ``available_tools()`` – list registered tool names
        • ``discover_and_register(path)`` – NO-OP stub (legacy)
        • ``execute(request)`` – run tool and wrap result in mapping
    """

    _registry: dict[str, type] = {}

    # ------------------------------------- API
    def register(self, tool_cls: type) -> None:  # noqa: D401 – simple wrapper
        """Register *tool_cls* exposing ``name`` attribute."""

        tool_name: str = getattr(tool_cls, "name", tool_cls.__name__)
        self._registry[tool_name] = tool_cls

    def available_tools(self) -> list[str]:  # noqa: D401 – simple list
        """Return sorted list of registered tool names."""

        return sorted(self._registry.keys())

    # Legacy stub – dynamic discovery via *.tool.py was removed in v0.5.
    def discover_and_register(self, _: Path) -> None:  # noqa: D401 – noop
        """No-op placeholder for legacy API surface."""

    # Async by design to integrate with orchestrator's await pattern.
    async def execute(self, request: "ToolRequest"):  # type: ignore[override]
        """Instantiate and run the requested *Skill*.

        The method auto-detects sync vs async ``execute`` implementation on
        the *Skill* instance to keep the shim lightweight.
        """

        tool_cls = self._registry.get(request.tool_name)
        if tool_cls is None:
            raise ValueError(f"Tool '{request.tool_name}' not registered")

        tool_instance = tool_cls()  # type: ignore[call-arg] – minimal ctor

        # Most *Skill* classes expose async ``execute``.  Handle both.
        exec_fn = getattr(tool_instance, "execute")
        if inspect.iscoroutinefunction(exec_fn):
            result = await exec_fn(request.inputs)  # type: ignore[arg-type]
        else:
            # Fallback – run in thread-pool if CPU-bound; keep simple for shim.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, exec_fn, request.inputs)

        return {"data": result}


# Export names
service_mod.ToolRequest = ToolRequest
service_mod.ToolService = ToolService

# Attach to module registry and parent package ------------------------------
sys.modules["ice_sdk.tools.service"] = service_mod
tools_pkg.service = service_mod  # type: ignore[attr-defined]

# ------------------------------------------------------------------
# Auto-register existing *Skill*s with ToolService so legacy *tool* nodes run
# ------------------------------------------------------------------
for _skill_name, _skill_obj in global_skill_registry:
    try:
        service_mod.ToolService._registry[_skill_name] = _skill_obj.__class__  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover – never fail import
        pass

# ------------------------------------------------------------------
# tools.system – domain-specific tool aliases (SumTool → SumSkill)
# ------------------------------------------------------------------

system_mod = ModuleType("ice_sdk.tools.system")
from ice_sdk.skills.system.sum_skill import SumSkill as _SumTool

system_mod.SumTool = _SumTool  # type: ignore[attr-defined]

sys.modules["ice_sdk.tools.system"] = system_mod
tools_pkg.system = system_mod  # type: ignore[attr-defined]

# ------------------------------------------------------------------
# tools.web – HttpRequestTool alias ----------------------------------------
# ------------------------------------------------------------------

web_mod = ModuleType("ice_sdk.tools.web")
from ice_sdk.skills.web.http_request_skill import HttpRequestSkill as _HttpRequestTool

web_mod.HttpRequestTool = _HttpRequestTool  # type: ignore[attr-defined]

sys.modules["ice_sdk.tools.web"] = web_mod
tools_pkg.web = web_mod  # type: ignore[attr-defined] 