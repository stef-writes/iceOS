"""Compatibility layer.

Importing ``app.tools`` is deprecated.  Use ``ice_tools`` instead.
This stub re-exports public names from ``ice_tools`` so existing code
continues to work while we migrate.
"""

from importlib import import_module
import sys

_mod = import_module("ice_tools")
globals().update(_mod.__dict__)

sys.modules.setdefault("app.tools", _mod)
