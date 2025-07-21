import logging
from typing import Any, Callable, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Type[Any])


def deprecated(version: str, replacement: str) -> Callable[[T], T]:
    """Class decorator that logs a deprecation warning *once* upon first instantiation.

    Parameters
    ----------
    version: str
        Version string when the symbol was deprecated.
    replacement: str
        Suggested fully‐qualified replacement.
    """

    def wrapper(cls: T) -> T:  # – simple decorator wrapper
        warned: bool = False

        def _warn() -> None:
            nonlocal warned
            if not warned:
                logger.warning(
                    "%s deprecated in %s. Use %s instead",
                    cls.__name__,
                    version,
                    replacement,
                )
                warned = True

        # Preserve original __init__ so behaviour stays identical ------------
        orig_init = cls.__init__  # type: ignore[attr-defined]

        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            _warn()
            orig_init(self, *args, **kwargs)  # type: ignore[misc]

        cls.__init__ = new_init  # type: ignore[assignment]
        return cls

    return wrapper
