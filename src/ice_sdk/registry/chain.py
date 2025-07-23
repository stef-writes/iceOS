from __future__ import annotations

"""Chain registry – reusable mini-workflow templates.

A *chain* is a directed acyclic graph composed of existing tools, agents,
units, or nested chains.  Registering chains allows blueprint authors to
reference them by name via ``nested_chain`` nodes.
"""

from typing import Any, Dict, Generator, Tuple
import warnings

from pydantic import BaseModel, PrivateAttr

__all__: list[str] = ["ChainRegistry", "global_chain_registry", "discover_builtin_chains"]


class ChainRegistrationError(RuntimeError):
    """Raised when a chain cannot be registered."""


class ChainRegistry(BaseModel):
    _chains: Dict[str, Any] = PrivateAttr(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}

    def register(self, name: str, chain: Any) -> None:
        if name in self._chains:
            raise ChainRegistrationError(f"Chain '{name}' already registered")
        # Optional structural validate hook
        validate_fn = getattr(chain, "validate", None)
        if callable(validate_fn):
            validate_fn()
        self._chains[name] = chain

    def get(self, name: str) -> Any:
        try:
            return self._chains[name]
        except KeyError as exc:
            raise ChainRegistrationError(f"Chain '{name}' not found") from exc

    # Minimal execute helper; actual orchestrator may call chain.run(ctx)
    async def run(self, name: str, context: Any):
        chain = self.get(name)
        run_fn = getattr(chain, "run")
        if not callable(run_fn):
            raise TypeError("Chain object missing 'run' method")
        return await run_fn(context)

    # Helpers
    def __iter__(self) -> Generator[Tuple[str, Any], None, None]:
        yield from self._chains.items()

    def __len__(self):  # pragma: no cover
        return len(self._chains)

# ---------------------------------------------------------------------------
# Discovery helper – import *ice_sdk.chains* modules ending with _chain ------
# ---------------------------------------------------------------------------


def discover_builtin_chains() -> None:  # noqa: D401
    """Import every module inside *ice_sdk.chains* so they self-register.

    Any import error is logged at WARNING level but does **not** raise,
    allowing the API to start even when optional chains have unmet deps.
    """

    import importlib
    import pkgutil
    import logging

    logger = logging.getLogger(__name__)

    try:
        pkg = importlib.import_module("ice_sdk.chains")
    except ModuleNotFoundError:  # pragma: no cover – chains package absent
        logger.debug("ice_sdk.chains package not found; skipping discovery")
        return

    if not hasattr(pkg, "__path__"):
        return

    for _finder, mod_name, _ispkg in pkgutil.walk_packages(pkg.__path__, prefix="ice_sdk.chains."):
        if not mod_name.endswith("_chain"):
            continue
        try:
            importlib.import_module(mod_name)
        except Exception as exc:  # pragma: no cover – log and continue
            logger.warning("Failed to import chain module %s: %s", mod_name, exc)


global_chain_registry: "ChainRegistry[Any]" = ChainRegistry()  # type: ignore[type-var]

# Shim warning
warnings.warn(
    "'global_chain_registry' lives in 'ice_sdk.registry.chain'.",
    DeprecationWarning,
    stacklevel=2,
) 