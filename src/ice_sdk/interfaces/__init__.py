"""Light-weight interfaces (Protocol definitions) that inner ice_sdk exposes
for other internal modules without importing higher-level packages.

Each interface captures the minimal surface needed from outer layers
(e.g., ScriptChain) so we don't violate onion-architecture boundaries.
"""
