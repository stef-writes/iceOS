from __future__ import annotations

"""Operator registry – canonical home for LLMOperator classes.

This file wraps the legacy *ProcessorRegistry* implementation but exposes a
clear name (OperatorRegistry) aligned with the taxonomy in
`docs/architecture/naming_conventions.md`.

Any new single-prompt LLM operator **must** register here, not in the old
`global_processor_registry`.
"""

import warnings
from typing import Any

from ice_sdk.tools.registry import SkillRegistry as _BaseRegistry

__all__: list[str] = [
    "OperatorRegistry",
    "global_operator_registry",
]


class OperatorRegistry(_BaseRegistry):
    """Registry dedicated to :class:`~ice_sdk.llm.operators.base.LLMOperator` classes."""

    pass  # No behaviour change – semantic alias for clarity


# Global instance -----------------------------------------------------------

global_operator_registry: "OperatorRegistry[Any]" = OperatorRegistry()  # type: ignore[type-var]

# ---------------------------------------------------------------------------
# Deprecation shim for legacy imports ---------------------------------------
# ---------------------------------------------------------------------------

warnings.warn(
    "'ice_sdk.registry.operator' is the canonical registry for LLM operators; "
    "importing via 'ice_sdk.processors.registry' is deprecated and will be removed in v1.2.",
    DeprecationWarning,
    stacklevel=2,
) 