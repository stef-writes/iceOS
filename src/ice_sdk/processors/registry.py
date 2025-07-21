"""In-memory registry for *Processor* subclasses.

Purpose
-------
1. Single source-of-truth for processor discovery (Rule 2 & 11).
2. Lightweight validation – each processor must expose ``validate`` and pass
   it at registration time (Rule 13).
3. Async execution helper so CLI/HTTP callers can invoke a processor without
   importing the concrete class.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Generic, Iterator, Mapping, Type, TypeVar

from pydantic import PrivateAttr

from .base import Processor

# Emit deprecation warning *after* imports to satisfy E402 -------------------
import warnings as _warnings  # isort: skip

_warnings.warn(
    "'ice_sdk.processors.registry' is deprecated; import from 'ice_sdk.registry.processor' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ProcessorRegistry",
    "global_processor_registry",
]


class ProcessorRegistrationError(RuntimeError):
    """Raised when a processor cannot be registered or resolved."""


ProcessorT = TypeVar("ProcessorT", bound="Processor[Any]")


class ProcessorRegistry(Generic[ProcessorT]):
    """Runtime registry mapping *name* → ``Processor`` subclass."""

    _processors: Dict[str, Type[ProcessorT]] = PrivateAttr(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    # ------------------------------------------------------------------
    # Registration ------------------------------------------------------
    # ------------------------------------------------------------------
    def register(self, processor_type: Type[ProcessorT]) -> Type[ProcessorT]:
        """Register a *Processor* subclass under *name*.

        The method instantiates the class *once* to verify that its
        ``validate`` method succeeds.  This keeps invalid processors from
        entering the execution path early.
        """

        if processor_type.name in self._processors:
            raise ProcessorRegistrationError(
                f"Processor '{processor_type.name}' already registered"
            )

        try:
            proc_instance = processor_type()  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover – defensive
            raise ProcessorRegistrationError(
                f"Processor '{processor_type.name}' failed to instantiate: {exc}"  # noqa: TRY003
            ) from exc

        if hasattr(proc_instance, "validate") and not proc_instance.validate():
            raise ProcessorRegistrationError(
                f"Processor '{processor_type.name}' failed self-validation"
            )

        self._processors[processor_type.name] = processor_type
        return processor_type

    # ------------------------------------------------------------------
    # Resolution --------------------------------------------------------
    # ------------------------------------------------------------------
    def get(self, name: str) -> Type[ProcessorT]:
        try:
            return self._processors[name]
        except KeyError as exc:
            raise ProcessorRegistrationError(f"Processor '{name}' not found") from exc

    # ------------------------------------------------------------------
    # Convenience async execution --------------------------------------
    # ------------------------------------------------------------------
    async def execute(
        self, name: str, payload: Mapping[str, Any]
    ) -> Any:  # noqa: ANN401
        """Instantiate & run *processor* with *payload* (async-compatible)."""

        proc_cls = self.get(name)
        proc_obj = proc_cls()  # type: ignore[call-arg]

        # Detect sync vs async *process*
        fn = getattr(proc_obj, "process")
        if asyncio.iscoroutinefunction(fn):
            return await fn(payload)  # type: ignore[arg-type]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fn, payload)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Dunder helpers ----------------------------------------------------
    # ------------------------------------------------------------------
    def __iter__(self) -> Iterator[tuple[str, Type[ProcessorT]]]:  # noqa: D401
        yield from self._processors.items()

    def __len__(self) -> int:  # noqa: D401 – simple helper
        return len(self._processors)


# Global default registry -----------------------------------------------------

global_processor_registry: "ProcessorRegistry[Processor[Any]]" = ProcessorRegistry()
