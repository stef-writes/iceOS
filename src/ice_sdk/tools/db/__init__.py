"""Stub DB-related tools for contract tests."""

from __future__ import annotations

from typing import Any, Optional

from ice_sdk.tools.base import ToolContext, function_tool

__all__ = [
    "sql_tool",
    "nosql_tool",
    "schema_validator_tool",
    "explain_plan_tool",
]


@function_tool()
async def sql_tool(
    ctx: ToolContext, query: str, params: Optional[dict[str, Any]] = None
):  # noqa: D401 – stub
    """Execute *query* against an in-memory SQLite DB (stub impl)."""

    # Very naive: return a fixed result or echo parameters for tests.
    if query.strip().lower().startswith("select"):
        return [{"id": params.get("id") if params else 1, "name": "foo"}]
    return {"rows_affected": 1}


# Simple in-memory collection store -----------------------------------------
_store: dict[str, dict[str, dict[str, Any]]] = {}


@function_tool()
async def nosql_tool(
    ctx: ToolContext,
    action: str,
    collection: str,
    key: str,
    payload: Optional[dict[str, Any]] = None,
):  # noqa: D401 – stub
    """Minimal NoSQL CRUD helper that backs the contract tests."""

    coll = _store.setdefault(collection, {})

    if action == "insert":
        coll[key] = payload or {}
        return {"id": key}
    if action == "get":
        return coll.get(key)
    if action == "update":
        if key not in coll:
            return {"error": "not found"}
        coll[key].update(payload or {})
        return coll[key]
    if action == "delete":
        coll.pop(key, None)
        return {"deleted": True}
    raise ValueError(f"Unsupported action: {action}")


@function_tool()
async def schema_validator_tool(
    ctx: ToolContext, schema: dict[str, Any], payload: dict[str, Any]
):  # noqa: D401 – stub
    """Return True when *payload* keys are subset of *schema* properties (stub)."""
    required = set(schema.get("required", []))
    props = schema.get("properties", {})
    valid = required.issubset(payload.keys()) and all(
        k in props for k in payload.keys()
    )
    return {"valid": valid}


@function_tool()
async def explain_plan_tool(ctx: ToolContext, query: str):  # noqa: D401 – stub
    """Return fake EXPLAIN plan as list of steps."""
    return {"plan": [f"SCAN -> {query[:20]}..."]}
