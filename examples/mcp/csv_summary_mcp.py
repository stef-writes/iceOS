#!/usr/bin/env python3
"""Demo: Register & execute a CSV → Summary workflow via MCP.

Usage (ensure FastAPI server is running on localhost:8000):
    python examples/mcp/csv_summary_mcp.py --csv /path/to/file.csv

This script demonstrates the *frontend-style* flow:
1. Build NodeSpec objects one by one (as a UI would).
2. POST a Blueprint to /api/v1/mcp/blueprints.
3. POST /runs to execute the blueprint.
4. Poll /runs/{id} until completion.
5. Print the summarizer output.

It relies on:
• csv_reader_skill (deterministic)  – no API key needed.
• summarizer_skill  – picks provider via env (OPENAI_API_KEY, ANTHROPIC_API_KEY, …).
"""
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ModuleNotFoundError:
    # Optional dependency – skip quietly when not installed.
    pass

from ice_core.models.mcp import Blueprint, NodeSpec
from ice_sdk.protocols.mcp.client import MCPClient

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = os.getenv("ICEOS_API", "http://localhost:8000")


def build_nodes(csv_path: Path, request_text: str) -> List[NodeSpec]:  # – helper
    """Build NodeSpec list for the CSV → Summary pipeline."""

    reader_spec = NodeSpec(
        id="reader",
        type="tool",  # Conversion logic in API maps "tool" → SkillNodeConfig
        tool_name="csv_reader",
        tool_args={"file_path": str(csv_path)},
        output_schema={  # Minimal schema so orchestrator mapping validator passes
            "headers": "list[str]",
            "rows": "list[dict[str, Any]]",
            "rows_json": "str",
            "total_rows": "int",
        },
    )

    summarizer_spec = NodeSpec(
        id="summarizer",
        type="tool",
        dependencies=["validator"],
        tool_name="summarizer",
        tool_args={
            "rows": "{rows_json}",  # Placeholder resolved by ContextBuilder
            "max_summary_tokens": 256,
        },
        input_mappings={
            "rows_json": {
                "source_node_id": "validator",
                "source_output_key": "clean_rows_json",
            }
        },
        output_schema={"summary": "str"},
    )

    # ------------------------------------------------------------------
    # 2. Line-item generator (LLM) --------------------------------------
    # ------------------------------------------------------------------

    line_gen = NodeSpec(
        id="line_gen",
        type="tool",
        dependencies=["reader"],
        tool_name="line_item_generator",
        tool_args={
            "request_text": request_text,
            "headers": "{headers_list}",
        },
        input_mappings={
            "headers_list": {
                "source_node_id": "reader",
                "source_output_key": "headers",
            }
        },
        output_schema={"row": "dict", "action": "str"},
    )

    # ------------------------------------------------------------------
    # 3. CSV writer ------------------------------------------------------
    # ------------------------------------------------------------------

    writer_spec = NodeSpec(
        id="writer",
        type="tool",
        dependencies=["line_gen"],
        tool_name="csv_writer",
        tool_args={
            "file_path": str(csv_path),
            "row": "{row_json}",
            "action": "{line_action}",
            "key_column": "Item_ID",
        },
        input_mappings={
            "row_json": {"source_node_id": "line_gen", "source_output_key": "row"},
            "line_action": {
                "source_node_id": "line_gen",
                "source_output_key": "action",
            },
        },
        output_schema={"success": "bool", "rows_json": "str"},
    )

    # ------------------------------------------------------------------
    # 4. Rows validator (after mutation) ---------------------------------
    # ------------------------------------------------------------------

    validator_spec = NodeSpec(
        id="validator",
        type="tool",
        dependencies=["writer"],
        tool_name="rows_validator",
        tool_args={
            "rows": "{rows_json}",
            "required_columns": [
                "Item_ID",
                "Name",
                "Qty",
                "Unit_Price",
            ],
            "drop_invalid": True,
        },
        input_mappings={
            "rows_json": {"source_node_id": "writer", "source_output_key": "rows_json"}
        },
        output_mappings={"clean_rows_json": "clean_rows_json"},
        output_schema={
            "valid": "bool",
            "clean_rows_json": "str",
            "errors": "list[str]",
        },
    )

    # Chain-of-thought insights node (LLM) ---------------------------------

    insights_spec = NodeSpec(
        id="insights",
        type="tool",
        dependencies=["summarizer"],
        tool_name="insights",
        tool_args={
            "summary": "{summary_text}",
            "max_tokens": 256,
        },
        input_mappings={
            "summary_text": {
                "source_node_id": "summarizer",
                "source_output_key": "summary",
            }
        },
        output_schema={"insights": "list[str]"},
    )

    return [
        reader_spec,
        line_gen,
        writer_spec,
        validator_spec,
        summarizer_spec,
        insights_spec,
    ]


async def main() -> None:  # – async entrypoint
    parser = argparse.ArgumentParser(description="MCP CSV → Summary demo")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=str,
        required=True,
        help="Path to CSV file to summarise",
    )
    parser.add_argument(
        "--request",
        dest="request_text",
        type=str,
        default="Add 10 units of 12mm plywood at $17 each (New).",
        help="Natural-language request to convert into a CSV row",
    )
    parser.add_argument(
        "--base-url",
        dest="base_url",
        type=str,
        default=DEFAULT_BASE_URL,
        help="MCP service base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    user_request = args.request_text.strip()
    if not user_request:
        raise SystemExit("--request text must not be empty")

    csv_path = Path(args.csv_path).expanduser().resolve()
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    # ------------------------------------------------------------------
    # 1. Build blueprint ------------------------------------------------
    # ------------------------------------------------------------------

    nodes = build_nodes(csv_path, user_request)
    blueprint = Blueprint(nodes=nodes)

    client = MCPClient(base_url=args.base_url)

    # ------------------------------------------------------------------
    # 2. Register blueprint --------------------------------------------
    # ------------------------------------------------------------------
    print("Registering blueprint …", end=" ")
    ack = await client.create_blueprint(blueprint)
    print("OK (id:", ack.blueprint_id + ")")

    # ------------------------------------------------------------------
    # 3. Start run ------------------------------------------------------
    # ------------------------------------------------------------------
    print("Starting run …", end=" ")
    run = await client.start_run(blueprint_id=ack.blueprint_id)
    print("run_id:", run.run_id)

    # ------------------------------------------------------------------
    # 4. Await result ---------------------------------------------------
    # ------------------------------------------------------------------
    print("Waiting for completion …")
    result = await client.await_result(run.run_id)

    # ------------------------------------------------------------------
    # 5. Inspect & print summary ---------------------------------------
    # ------------------------------------------------------------------
    if result.success and isinstance(result.output, dict):
        summarizer_node = result.output.get("summarizer")
        if summarizer_node and getattr(summarizer_node, "output", None):
            summary: str = summarizer_node.output.get("summary", "<missing>")
            print("\n=== Summary ===\n" + summary)

        insights_node = result.output.get("insights")
        if insights_node and getattr(insights_node, "output", None):
            ins = insights_node.output.get("insights", [])
            if ins:
                print("\n=== Insights ===")
                for idx, insight in enumerate(ins, 1):
                    print(f"{idx}. {insight}")
        else:
            print("\nRun succeeded but summarizer output missing. Full payload:")
            print(result.output)
    else:
        print("Run failed:", result.error)


if __name__ == "__main__":
    asyncio.run(main())
