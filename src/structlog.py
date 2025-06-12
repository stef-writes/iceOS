import logging
from types import SimpleNamespace
from typing import Any, Callable, Optional

__all__ = [
    "get_logger",
    "configure",
    "is_configured",
    "make_filtering_bound_logger",
    "processors",
]

# ---------------------------------------------------------------------------
# Minimal shim for structlog used only in test/dev environments.  It exposes
# just enough surface-area so that existing import sites continue to work when
# the real library is not installed.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Bound logger – swallows *structlog* style keyword arguments gracefully.
# ---------------------------------------------------------------------------


class _BoundLogger:
    """Mimic the bound logger API of *structlog* using stdlib logging.*

    It formats any structured keyword arguments as ``key=value`` pairs appended
    to the message so that calls such as:

        logger.info("Completed", chain="my_chain", duration=1.23)

    do not raise *TypeError* under the stub implementation.
    """

    _LEVEL_METHODS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    # Dynamically create proxy methods for standard levels ----------------
    def __getattr__(self, name: str):  # noqa: D401
        if name in self._LEVEL_METHODS:
            level = self._LEVEL_METHODS[name]

            def _log(msg: str, *args: Any, **kwargs: Any):  # noqa: D401
                if kwargs:
                    kv = " ".join(f"{k}={v}" for k, v in kwargs.items())
                    msg_ = f"{msg} | {kv}"
                else:
                    msg_ = msg
                self._logger.log(level, msg_, *args)

            return _log

        # Fallback to underlying logger attribute (bind, etc.).
        return getattr(self._logger, name)


def get_logger(name: Optional[str] = None):  # type: ignore[override]
    """Return a stub *structlog* logger that accepts keyword fields."""

    return _BoundLogger(logging.getLogger(name or __name__))


_configured = True  # Treat the shim as already configured to avoid calls.


def is_configured() -> bool:  # noqa: D401 – preserve original name
    """Always return *True* so callers skip expensive configuration."""

    return _configured


def configure(*_args: Any, **_kwargs: Any) -> None:  # noqa: D401 – preserve name
    """No-op replacement for ``structlog.configure``."""

    # The real structlog mutates global state; the stub ignores it.
    return None


# ---------------------------------------------------------------------------
# Stub *processors* namespace with attributes that return identity functions.
# ---------------------------------------------------------------------------


def _identity_processor(*_args: Any, **_kwargs: Any) -> Callable[[Any, str, dict], dict]:
    """Return a processor that passes the event dictionary through unchanged."""

    def _processor(_logger: Any, _name: str, event_dict: dict) -> dict:  # noqa: D401
        return event_dict

    return _processor


processors = SimpleNamespace(  # type: ignore[assignment]
    TimeStamper=lambda *a, **k: _identity_processor(),
    add_log_level=_identity_processor(),
    StackInfoRenderer=_identity_processor(),
    format_exc_info=_identity_processor(),
    JSONRenderer=_identity_processor(),
)


def make_filtering_bound_logger(*_args: Any, **_kwargs: Any):  # noqa: D401
    """Return a passthrough logger wrapper used by ``structlog.configure``."""

    def _wrapper(logger: logging.Logger):  # type: ignore[override]
        return logger

    return _wrapper 