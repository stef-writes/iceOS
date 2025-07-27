"""LLM Operators package.

This subpackage hosts concrete LLM-backed processors that should not be confused
with deterministic *skills* or side-effectful *tools*.
"""

from importlib import import_module
from typing import TYPE_CHECKING

# Auto-import concrete operator modules so that `from ice_sdk.llm.operators import X`
# works without clients needing to know the file structure.  Keep list short to
# avoid heavy import graphs.

_module_names = [
    "line_item_generator",
    "summarizer",
    "insights",
]

if not TYPE_CHECKING:  # pragma: no cover – runtime side
    for _name in _module_names:
        try:
            import_module(f"{__name__}.{_name}")
        except ModuleNotFoundError:  # pragma: no cover – safety guard
            continue

# Re-export for convenience --------------------------------------------------
from .line_item_generator import LineItemGeneratorOperator  # noqa: E402 F401
from .summarizer import SummarizerOperator  # noqa: E402 F401
from .insights import InsightsOperator  # noqa: E402 F401

# ----------------------------------------
# Register all operators with the global ProcessorRegistry so that they are
# discoverable by orchestrators that rely on `registry.processor` look-ups.
# ----------------------------------------

from ice_core.unified_registry import registry
from ice_core.models import NodeType

for _op in (
    LineItemGeneratorOperator,
    SummarizerOperator,
    InsightsOperator,
):
    try:
        registry.register_class(NodeType.LLM, _op.name, _op)  # type: ignore[arg-type]
    except Exception:  # pragma: no cover – duplicate or validation failure
        pass 