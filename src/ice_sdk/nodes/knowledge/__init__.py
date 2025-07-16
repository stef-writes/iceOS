"""Knowledge-centric nodes for *ice_sdk*.

Currently exposes :class:`EnterpriseKBNode` integrating the new *KnowledgeService*.
"""

from __future__ import annotations

from .enterprise_kb_node import EnterpriseKBNode  # noqa: F401

__all__: list[str] = [
    "EnterpriseKBNode",
]
