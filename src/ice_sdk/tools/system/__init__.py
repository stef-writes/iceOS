"""System tool registry.

Only imports modules that actually exist in the package directory so that
optional tools can be removed without breaking application start-up.
"""

from importlib import import_module
from pathlib import Path
from typing import List

from ice_core.models import NodeType

from ice_core.unified_registry import registry

pkg_dir = Path(__file__).parent


def _discover_tool_modules() -> List[str]:
    """Return dotted module names for all *_tool.py files in this package."""
    modules: List[str] = []
    for path in pkg_dir.glob("*_tool.py"):
        if path.name == "__init__.py":
            continue
        modules.append(f"{__name__}.{path.stem}")
    return modules


for mod_path in _discover_tool_modules():
    try:
        mod = import_module(mod_path)
        # Expect each module to expose a class named *...Tool* matching the stem
        tool_cls_name = "".join([part.capitalize() for part in mod_path.split(".")[-1].split("_")])
        tool_cls = getattr(mod, tool_cls_name)
        tool_instance = tool_cls()
        registry.register_instance(NodeType.TOOL, tool_instance.name, tool_instance)
    except Exception:  # pragma: no cover – ignore faulty optional tools
        continue
