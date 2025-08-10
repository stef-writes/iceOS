from __future__ import annotations

"""Orchestrator-side plugin loader.

This module hosts the explicit registration of first-party tools to avoid
import-time side effects and keeps `ice_core` free of `ice_tools` references.
"""

from ice_core.unified_registry import register_tool_factory


def load_first_party_tools() -> int:
    """Register first-party generated tools.

    Returns:
        int: Number of tools registered (best-effort).
    """
    try:
        import pkgutil

        import ice_tools.generated as _gen

        count = 0
        for _m in pkgutil.iter_modules(_gen.__path__):  # type: ignore[attr-defined]
            module_name = _m.name
            factory_func = f"create_{module_name}"
            tool_name = module_name
            import_path = f"ice_tools.generated.{module_name}:{factory_func}"
            try:
                register_tool_factory(tool_name, import_path)
                count += 1
            except Exception:
                # Some modules may not expose a factory or may already be
                # registered. Keep going – registration is idempotent per path.
                continue
        return count
    except ModuleNotFoundError:
        return 0
