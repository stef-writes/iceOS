"""Re-exported stub explain_plan_tool for contract tests."""

from __future__ import annotations

from importlib import import_module

explain_plan_tool = import_module("ice_sdk.tools.db").explain_plan_tool  # type: ignore[attr-defined]

__all__ = ["explain_plan_tool"]
