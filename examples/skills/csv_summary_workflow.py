#!/usr/bin/env python3
"""Workflow demo: CSV → Summary via *ice_orchestrator*.

Run:
    python examples/skills/csv_summary_workflow.py

This script builds a two-node Workflow:
1. ``csv_reader`` skill parses a local CSV.
2. ``summarizer`` skill generates a high-level summary of the rows.

Both skills are registered globally, so the orchestrator can resolve them
through the *tool* executor without additional wiring.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

# InputMapping and SkillNodeConfig now live in *ice_core.models.node_models*.
from ice_core.models.node_models import InputMapping, SkillNodeConfig

# NOTE: The builder service was removed; construct the workflow directly.
# Updated imports to match current module locations.
from ice_orchestrator.workflow import Workflow
from ice_sdk.skills.system.csv_reader_skill import CSVReaderSkill

# ---------------------------------------------------------------------------
# Ensure sample CSV exists next to the script --------------------------------
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent

parser = argparse.ArgumentParser(description="CSV → Summary workflow demo")
parser.add_argument("--csv", dest="csv_path", help="Path to CSV file", default=None)
args = parser.parse_args()

if args.csv_path:
    CSV_PATH = Path(args.csv_path).expanduser().resolve()
    if not CSV_PATH.exists():
        raise SystemExit(f"CSV file not found: {CSV_PATH}")
else:
    CSV_PATH = DATA_DIR / "sample.csv"
    if not CSV_PATH.exists():
        CSV_PATH.write_text(
            "name,score\nAlice,85\nBob,92\nCharlie,78\n", encoding="utf-8"
        )

# ---------------------------------------------------------------------------
# Build Workflow nodes -------------------------------------------------------
# ---------------------------------------------------------------------------

# Node 1: CSV Reader – use *CSV_PATH* resolved above
csv_node = SkillNodeConfig(
    id="reader",
    tool_name="csv_reader",
    tool_args={"file_path": str(CSV_PATH)},
    output_schema=CSVReaderSkill.OutputModel.model_json_schema(),
)

# Node 2: Summarizer
summarizer_node = SkillNodeConfig(
    id="summarizer",
    tool_name="summarizer",
    tool_args={
        "rows": "{rows_json}",  # Bind to CSV node's JSON output
        "max_summary_tokens": 256,
    },
    dependencies=["reader"],
    input_mappings={
        "rows_json": InputMapping(
            source_node_id="reader", source_output_key="rows_json"
        )
    },
)

# ---------------------------------------------------------------------------
# Build Workflow and run it directly (no builder service required) -----------
# ---------------------------------------------------------------------------

workflow = Workflow(nodes=[csv_node, summarizer_node], name="CSV Analysis Pipeline")


async def main() -> None:  # – script entrypoint
    result = await workflow.execute()

    print("\n=== Workflow Output ===")
    if result.success and isinstance(result.output, dict):
        # Fetch summarizer node output for convenience
        summarizer_res = result.output.get("summarizer")
        if summarizer_res and getattr(summarizer_res, "output", None):
            print("Summary:\n", summarizer_res.output.get("summary"))
        else:
            print("Full result object:", result.output)
    else:
        print("Workflow failed:", result.error)


if __name__ == "__main__":
    asyncio.run(main())
