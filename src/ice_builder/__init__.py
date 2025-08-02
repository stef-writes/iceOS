"""ice_builder - Unified workflow building package.

This package combines the fluent DSL builders and natural language processing
capabilities into a single, cohesive interface for creating iceOS workflows.
"""

from importlib import metadata

from .dsl import *  # noqa: F401,F403
from .nl import append_tool_node, create_partial_blueprint  # public NL entry

__all__ = dsl.__all__ + ["create_partial_blueprint", "append_tool_node"]  # type: ignore[name-defined]
__version__ = metadata.version("iceos") 