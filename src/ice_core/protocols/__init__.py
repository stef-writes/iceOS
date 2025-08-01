"""Core protocol definitions for iceOS.

This package contains all abstract interfaces and protocols that define
contracts between layers. No implementations should be in this package.

Layer Rules:
1. NO external dependencies (pure Python only)
2. NO I/O operations
3. Define contracts only, no implementations
"""

from .embedder import IEmbedder
from .node import INode
from .registry import IRegistry
from .tool import ITool
from .vector import IVectorIndex
from .workflow import IWorkflow

__all__ = [
    "INode",
    "ITool", 
    "IRegistry",
    "IVectorIndex",
    "IEmbedder",
    "IWorkflow",
] 