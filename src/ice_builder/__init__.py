"""ice_builder - Unified workflow building package.

This package combines the fluent DSL builders and natural language processing
capabilities into a single, cohesive interface for creating iceOS workflows.
"""

from importlib import metadata

from . import dsl as _dsl  # explicit import for __all__ construction
from .dsl import *  # noqa: F401,F403 – re-export builder symbols
from .nl import append_tool_node, create_partial_blueprint  # public NL entry

# Combine DSL exports with high-level NL helpers
__all__ = _dsl.__all__ + ["create_partial_blueprint", "append_tool_node"]
__version__ = metadata.version("iceos") 