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

import asyncio
from pathlib import Path
import sys
import argparse

from ice_sdk.models.node_models import InputMapping, SkillNodeConfig
from ice_sdk.skills.system.csv_reader_skill import CSVReaderSkill
from ice_sdk.skills.system.summarizer_skill import SummarizerSkill
from ice_orchestrator.workflow import Workflow
from ice_orchestrator.workflow_execution_context import (  # Proper public API
    NodeConfig,
    InputMapping
)
from ice_api.services.builder import WorkflowBuilderService  # Service interface

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

# Node 1: CSV Reader
csv_node = SkillNodeConfig(
    id="reader",
    tool_name="csv_reader",
    tool_args={"file_path": "items.csv"},
    output_schema=CSVReaderSkill.OutputModel.model_json_schema()  # Explicit schema
)

# Node 2: Summarizer 
summarizer_node = SkillNodeConfig(
    id="summarizer",
    tool_name="summarizer",
    tool_args={
        "rows": "{rows_json}",  # Bind to CSV node's JSON output
        "max_summary_tokens": 256
    },
    dependencies=["reader"],
    input_mappings={
        "rows_json": InputMapping(
            source_node_id="reader",
            source_output_key="rows_json"
        )
    }
)

# Create and execute workflow
workflow = Workflow(
    nodes=[csv_node, summarizer_node],
    name="CSV Analysis Pipeline"
)


async def main() -> None:  # noqa: D401 – script entrypoint
    builder = WorkflowBuilderService()
    
    # Build via service interface instead of direct configs
    workflow = await builder.create_workflow(
        name="CSV Analysis Pipeline",
        nodes=[
            {
                "id": "reader",
                "tool": "csv_reader",
                "params": {"file_path": str(CSV_PATH)},  # Use validated path
                "validate": True  # Rule 13
            },
            {
                "id": "summarizer", 
                "tool": "summarizer",
                "deps": ["reader"],
                "input_mappings": {
                    "rows_json": {"reader": "rows_json"} 
                },
                "validate": True
            }
        ]
    )
    
    # Execute through service with metrics
    result = await workflow.execute_with_metrics()

    print("\n=== Workflow Output ===")
    if result.success:
        print(result.output)
    else:
        print("Workflow failed:", result.error)


if __name__ == "__main__":
    asyncio.run(main()) 