"""ice_builder - Unified workflow building package.

This package combines the fluent DSL builders and natural language processing
capabilities into a single, cohesive interface for creating iceOS workflows.
"""

from importlib import metadata

# Stable public surface for code generators
from .public import *  # noqa: F401,F403 – re-export for convenience

from . import dsl as _dsl  # internal DSL (full surface)
from .dsl import *  # noqa: F401,F403 – legacy re-export
from .nl import append_tool_node, create_partial_blueprint  # public NL entry

from typing import List as _List

_public_all: _List[str] = globals().get("__all__", [])  # type: ignore[arg-type]
__all__: _List[str] = _public_all + _dsl.__all__ + ["create_partial_blueprint", "append_tool_node"]
__version__ = metadata.version("iceos") 