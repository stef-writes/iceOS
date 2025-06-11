"""Compatibility shim for the old ``app.models`` import path.

All model classes have moved to ``ice_sdk.models``.  This module re-exports
those symbols so existing imports keep working during the migration.
"""

from importlib import import_module
import sys

_node_models = import_module("ice_sdk.models.node_models")
_config = import_module("ice_sdk.models.config")

globals().update(_node_models.__dict__)
globals().update(_config.__dict__)

sys.modules.setdefault("app.models.node_models", _node_models)
sys.modules.setdefault("app.models.config", _config)
