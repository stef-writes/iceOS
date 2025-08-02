"""Core-level service locator and dependency-injection helpers.

This module relocates the *ServiceLocator* previously hosted under
``ice_sdk.services.locator`` into the **core** layer so that:

1. Lower layers (core, builder) can depend on the locator without importing
   from the now-retired *ice_sdk* package.
2. Upper layers (orchestrator, api) can continue to register concrete
   services at runtime without layer violations.

The implementation is imported verbatim to avoid any functional drift.
Once all call-sites have been migrated to ``ice_core.services``, the old
proxy module in *ice_sdk* will be deleted.
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
