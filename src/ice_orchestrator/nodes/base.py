"""Compatibility shim – legacy import path ``ice_orchestrator.nodes.base.BaseNode``.

The real implementation lives in ``ice_sdk.base_node``.  Importing this module
re-exports *that* class so existing code keeps working without changes.
"""

from ice_sdk.base_node import BaseNode  # noqa: F401

__all__: list[str] = ["BaseNode"] 