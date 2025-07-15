"""Stub evaluator executor module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _EvalResult:  # noqa: D401 – helper container
    success: bool
    output: dict[str, Any]


async def evaluator_executor(
    _chain: Any, cfg: Any, ctx: dict[str, Any]
):  # noqa: D401 – stub
    """Naïve text similarity evaluator used by contract tests."""

    candidate = ctx.get("candidate", "")
    reference = getattr(cfg, "reference", "")
    threshold = getattr(cfg, "threshold", 0.5)

    score = 1.0 if candidate == reference else 0.0
    passed = score >= threshold

    return _EvalResult(success=True, output={"passed": passed, "score": score})
