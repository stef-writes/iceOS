from typing import Any, Callable, List, Optional, ParamSpec, Protocol, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")

# ---------------------------------------------------------------------------
# Core Click exception hierarchy
# ---------------------------------------------------------------------------

class ClickException(Exception):
    """Base click exception"""

class UsageError(ClickException):
    """Raised on usage errors"""

# ---------------------------------------------------------------------------
# Basic parameter helper classes (subset)
# ---------------------------------------------------------------------------

class Choice:
    def __init__(self, choices: List[str], case_sensitive: bool = ...) -> None: ...

class Path:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

# ---------------------------------------------------------------------------
# Command / Group stubs ------------------------------------------------------
# ---------------------------------------------------------------------------

class Command(Protocol):
    """Represents a Click command object."""

    name: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

class Group(Command, Protocol):
    """Represents a Click command group object."""

    def add_command(self, cmd: Command, name: Optional[str] = ...) -> None: ...
    def command(
        self, *args: Any, **kwargs: Any
    ) -> Callable[[Callable[_P, _R]], Command]: ...
    def group(
        self, *args: Any, **kwargs: Any
    ) -> Callable[[Callable[_P, _R]], "Group"]: ...

# ---------------------------------------------------------------------------
# Decorators -----------------------------------------------------------------
# ---------------------------------------------------------------------------

def command(*args: Any, **kwargs: Any) -> Callable[[Callable[_P, _R]], Command]: ...
def group(*args: Any, **kwargs: Any) -> Callable[[Callable[_P, _R]], Group]: ...
def argument(
    *args: Any, **kwargs: Any
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...
def option(
    *args: Any, **kwargs: Any
) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...

# ---------------------------------------------------------------------------
# Utilities ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def echo(msg: str, **kwargs: Any) -> None: ...
def get_current_context() -> Any: ...
