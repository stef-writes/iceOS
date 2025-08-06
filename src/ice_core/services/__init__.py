"""Core-level service locator and dependency-injection helpers.

This module provides the *ServiceLocator* for dependency injection and service
registration across the iceOS architecture.

The ServiceLocator allows:
1. Lower layers (core, builder) to register and access services
2. Upper layers (orchestrator, api) to register concrete services at runtime
3. Cross-layer communication through stable service interfaces

The implementation is designed to avoid layer violations while providing
flexible service discovery and dependency injection.
"""

from __future__ import annotations

from .locator import ServiceLocator as ServiceLocator  # type: ignore

# NOTE: We *import* the original implementation so existing singletons are
# shared.  After the migration we will delete the old module and inline the
# class definition here, but during the transition this avoids duplicate
# registries.


__all__: list[str] = [
    "ServiceLocator",
]

# Public alias -----------------------------------------------------------------
ServiceLocator = ServiceLocator
