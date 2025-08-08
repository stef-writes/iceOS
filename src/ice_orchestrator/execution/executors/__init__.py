"""Runtime node executors package.

Importing *ice_orchestrator.execution.executors* auto-registers all built-in
node executors by importing the `builtin` sub-package, which triggers each
module’s `@register_node` side-effects.
"""

from importlib import import_module

# Import builtin executors to populate the global registry
import_module(__name__ + ".builtin")
