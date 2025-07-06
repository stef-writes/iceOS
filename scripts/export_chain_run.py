#!/usr/bin/env python3
"""Export detailed execution data for a ScriptChain.

Usage
-----
python scripts/export_chain_run.py path/to/chain.py [--out result.json]

The script:
1. Dynamically loads the chain module.
2. Runs the chain (async).
3. Collects, for every node:
   • prompt (if present)
   • resolved *input_context* passed to the node
   • output / error from execution
4. Writes a single JSON document to stdout or *--out* file.

This helper avoids depending on the *ice* CLI so it can be reused in
notebooks / CI pipelines without side-effects.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

from ice_orchestrator.script_chain import ScriptChain
from ice_sdk.context import GraphContextManager

# ---------------------------------------------------------------------------
# Module loading helper (simplified from ice CLI) ---------------------------
# ---------------------------------------------------------------------------


def _load_module_from_path(path: Path) -> ModuleType:
    if not path.exists():
        raise FileNotFoundError(path)

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:  # pragma: no cover – safety check
        raise ImportError(f"Cannot import {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


def _load_chain(path: Path) -> ScriptChain:
    mod = _load_module_from_path(path)

    if hasattr(mod, "chain") and isinstance(mod.chain, ScriptChain):  # type: ignore[attr-defined]
        return mod.chain  # type: ignore[attr-return-value]
    if hasattr(mod, "get_chain") and callable(mod.get_chain):  # type: ignore[attr-defined]
        chain = mod.get_chain()
        if isinstance(chain, ScriptChain):
            return chain
    # Fall back – scan for ScriptChain instances in globals
    for value in mod.__dict__.values():
        if isinstance(value, ScriptChain):
            return value
    raise ValueError("No ScriptChain instance found in module")


# ---------------------------------------------------------------------------
# Data extraction -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _collect_run_data(
    chain: ScriptChain, result: Any
) -> Dict[str, Any]:  # noqa: ANN401 – free-form dict
    ctx_mgr: GraphContextManager = chain.context_manager

    data: Dict[str, Any] = {
        "chain_name": chain.name,
        "success": result.success,
        "duration": result.execution_time,
        "nodes": {},
    }

    for node_id, cfg in chain.nodes.items():
        node_entry: Dict[str, Any] = {
            "id": node_id,
            "type": getattr(cfg, "type", "unknown"),
            "prompt": getattr(cfg, "prompt", None),
            "input_mappings": getattr(cfg, "input_mappings", None),
            # Resolved inputs captured by ContextManager ------------------
            "inputs": (
                ctx_mgr.get_node_context(node_id)
                if hasattr(ctx_mgr, "get_node_context")
                else None
            ),
        }

        exec_res = result.output.get(node_id)
        if exec_res is not None:
            node_entry.update(
                {
                    "success": exec_res.success,
                    "error": exec_res.error,
                    "output": exec_res.output,
                }
            )
        data["nodes"][node_id] = node_entry

    return data


# ---------------------------------------------------------------------------
# Main ----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D401 – script entry-point
    parser = argparse.ArgumentParser(
        description="Run a ScriptChain and export detailed JSON results."
    )
    parser.add_argument(
        "chain_path", type=Path, help="Path to .py file containing a ScriptChain"
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="Output JSON file (default: stdout)"
    )
    args = parser.parse_args()

    chain = _load_chain(args.chain_path)

    # Execute ----------------------------------------------------------------
    result = asyncio.run(chain.execute())

    payload = _collect_run_data(chain, result)

    serialized = json.dumps(payload, indent=2, default=str)

    if args.out is None:
        print(serialized)
    else:
        args.out.write_text(serialized, encoding="utf-8")
        print(f"Wrote results → {args.out}")


if __name__ == "__main__":
    main()
