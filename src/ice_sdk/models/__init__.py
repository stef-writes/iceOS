"""Temporary compatibility layer.

Exposes the original model classes under the new package path so code can
start importing ``ice_sdk.models.*`` while we gradually move files out of
``app.models``.
"""

from importlib import import_module
import sys

# Old modules still live under app.models.*
_old_node_models = import_module("app.models.node_models")
_old_config = import_module("app.models.config")

# Re-export their names so ``from ice_sdk.models import NodeConfig`` works.
globals().update(_old_node_models.__dict__)
globals().update(_old_config.__dict__)

# Also register them in sys.modules under the new fully-qualified names so that
# ``import ice_sdk.models.node_models`` continues to give the same module
# object.
sys.modules.setdefault("ice_sdk.models.node_models", _old_node_models)
sys.modules.setdefault("ice_sdk.models.config", _old_config) 