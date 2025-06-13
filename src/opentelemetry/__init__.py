import sys
import types
from importlib import import_module as _import_module
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Minimal *opentelemetry* shim for test/dev environments.
# ---------------------------------------------------------------------------

# A very small Span object that supports the handful of methods used internally.
class _Span:
    def __enter__(self) -> "_Span":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:  # noqa: ANN001
        # `False` signals the context manager should *not* suppress exceptions.
        return False

    # API compatibility helpers -------------------------------------------------
    def set_attribute(self, *_args: Any, **_kwargs: Any) -> None:  # noqa: D401
        pass

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:  # noqa: D401
        pass

    def end(self) -> None:  # noqa: D401
        pass


class _Tracer:
    def start_as_current_span(self, *_args: Any, **_kwargs: Any) -> _Span:  # noqa: D401
        return _Span()


# status codes mimic the real enum shape but are simple constants here
class _StatusCode:
    ERROR = "ERROR"


class _Status:  # pylint: disable=too-few-public-methods
    def __init__(self, _status_code: str = "OK", _description: str | None = None):
        self.status_code = _status_code
        self.description = _description


# ----------------------------------------------------------------------------
# ``opentelemetry.trace`` sub-module ------------------------------------------------
# ----------------------------------------------------------------------------

_trace_mod = types.ModuleType("opentelemetry.trace")
_trace_mod.get_tracer = lambda _name=None: _Tracer()  # type: ignore[attr-defined,assignment]
_trace_mod.Status = _Status  # type: ignore[attr-defined,assignment]
_trace_mod.StatusCode = _StatusCode  # type: ignore[attr-defined,assignment]

# Expose the sub-module so `from opentelemetry import trace` works
sys.modules[__name__ + ".trace"] = _trace_mod

# Re-export to consumers of `import opentelemetry.trace as trace`
trace = _import_module(__name__ + ".trace")  # type: ignore[invalid-name]

__all__ = [
    "trace",
] 