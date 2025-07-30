"""Tool package for FB Marketplace Seller use case."""

from importlib import import_module as _import_module
from typing import TYPE_CHECKING

# Re-export tool classes for convenient absolute imports
_tool_modules = [
    "read_inventory_csv",
    "dedupe_items",
    "ai_enrichment",
    "facebook_publisher",
    "facebook_api_client",
    "activity_simulator",
    "inquiry_responder",
    "market_research",
    "price_updater",
    "facebook_messenger",
]

__all__ = []
for _mod in _tool_modules:
    mod = _import_module(f"{__name__}.{_mod}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if getattr(obj, "__module__", "").startswith(__name__):
            globals()[attr] = obj
            __all__.append(attr)

del _import_module, _tool_modules, _mod, mod, attr, obj, TYPE_CHECKING
