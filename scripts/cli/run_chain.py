#!/usr/bin/env python3
"""CLI: run a Workflow JSON file via MVPContract.

Usage::

    ice run-chain path/to/chain.json [--estimate] [--out result.json]

* ``--estimate`` prints rough USD cost using `estimate_chain_cost` and exits.
* Without ``--estimate`` it executes the chain and prints (or writes) results.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from ice_core.utils.cost import estimate_chain_cost

from ice_orchestrator.contracts.mvp_contract import MVPContract


def _load_spec(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception as err:  # pragma: no cover
        raise SystemExit(f"Failed to parse JSON: {err}")


def main() -> None:  # noqa: D401 – entrypoint
    parser = argparse.ArgumentParser(description="Run an iceOS Workflow JSON spec")
    parser.add_argument("spec", type=Path, help="Path to chain JSON spec")
    parser.add_argument(
        "--estimate", action="store_true", help="Only estimate cost and exit"
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="Write execution result to file"
    )
    args = parser.parse_args()

    spec = _load_spec(args.spec)

    if args.estimate:
        cost = estimate_chain_cost(spec)
        print(json.dumps({"estimated_cost_usd": cost}, indent=2))
        return

    contract = MVPContract()
    result = contract.execute_chain(spec)

    payload = json.dumps(result, indent=2)

    if args.out is None:
        print(payload)
    else:
        args.out.write_text(payload, "utf-8")
        print(f"Wrote results → {args.out}")


if __name__ == "__main__":
    main()
