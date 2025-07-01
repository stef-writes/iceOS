from importlib import import_module

# Lazily import sub-command groups so importing this package remains cheap.
for _mod in ("tool",):
    try:
        globals().update(import_module(f"ice_cli.commands.{_mod}").__dict__)
    except Exception:  # pragma: no cover – defensive
        pass

__all__ = ["tool_app", "get_tool_service"]
