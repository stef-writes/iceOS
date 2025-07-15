"""Re-exported stub schema_validator_tool for contract tests."""

from __future__ import annotations

from importlib import import_module

schema_validator_tool = import_module("ice_sdk.tools.db").schema_validator_tool  # type: ignore[attr-defined]

__all__ = ["schema_validator_tool"]
