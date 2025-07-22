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
from ice_core.models.node_models import NodeSpec, NodeType
from ice_sdk.registry.tool import global_tool_registry
from ice_sdk.registry.operator import global_operator_registry

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = os.getenv("ICEOS_API", "http://localhost:8000")


def build_nodes(csv_path: Path, request_text: str) -> List[NodeSpec]:  # – helper
    """Build NodeSpec list for the CSV → Summary pipeline."""

    reader_spec = NodeSpec(
        id="reader",
        type=NodeType.TOOL,
        tool_name="csv_reader",
        tool_args={"file_path": str(csv_path)},
        input_schema={"file_path": "str"},
        output_schema={
            "headers": "list[str]",
            "rows": "list[dict]",
            "rows_json": "str",
            "total_rows": "int",
        },
    )

    summarizer_spec = NodeSpec(
        id="summarizer",
        type=NodeType.LLM,
        dependencies=["validator"],
        operator_name="summarizer",
        operator_args={
            "validation_results": {"source_node": "validator", "source_output": "errors"}
        },
        output_schema={"summary": "str", "score": "float"},
    )

    # ------------------------------------------------------------------
    # 2. Line-item generator (LLM) --------------------------------------
    # ------------------------------------------------------------------

    line_gen = NodeSpec(
        id="line_gen",
        type=NodeType.LLM,
        dependencies=["reader"],
        operator_name="line_item_generator",
        operator_args={
            "request_text": request_text,
            "headers": {"source_node": "reader", "source_output": "headers"},
        },
        output_schema={
            "row": "dict",
            "action": "str",
        },
    )

    # ------------------------------------------------------------------
    # 3. CSV writer ------------------------------------------------------
    # ------------------------------------------------------------------

    writer_spec = NodeSpec(
        id="writer",
        type=NodeType.TOOL,
        dependencies=["line_gen"],
        tool_name="csv_writer",
        tool_args={
            "file_path": str(csv_path),
            "action": "append",
            "key_column": "id",
        },
        input_mappings={
            "row": {"source_node_id": "line_gen", "source_output_key": "row"},
            "action": {"source_node_id": "line_gen", "source_output_key": "action"},
        },
        output_schema={
            "success": "bool",
            "rows": "list[dict]",  # Changed from rows_json
        },
        input_schema={
            "row": "dict",
            "action": "str",
        },
    )

    # ------------------------------------------------------------------
    # 4. Rows validator (after mutation) ---------------------------------
    # ------------------------------------------------------------------

    validator_spec = NodeSpec(
        id="validator",
        type=NodeType.TOOL,
        dependencies=["writer"],  # Now depends on writer instead of reader
        tool_name="rows_validator",
        tool_args={
            "required_columns": ["id", "name", "price"],
            "drop_invalid": True,
        },
        input_mappings={
            "rows": {"source_node_id": "writer", "source_output_key": "rows"},
        },
        output_schema={
            "valid_rows": "list[dict]",
            "invalid_count": "int",
        },
        input_schema={
            "rows": "list[dict]",
        },
    )

    # Chain-of-thought insights node (LLM) ---------------------------------

    insights_spec = NodeSpec(
        id="insights",
        type=NodeType.LLM,
        dependencies=["summarizer"],
        operator_name="insights",
        operator_args={
            "summary_text": {"source_node": "summarizer", "source_output": "summary"}
        },
        output_schema={"insights": "list[str]"},
    )

    return [
        reader_spec,
        line_gen,
        writer_spec,
        validator_spec,  # Moved after writer
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

    # Optional JSON output file ---------------------------------------
    parser.add_argument(
        "--json-out",
        dest="json_out",
        type=str,
        default=None,
        help="Path to write structured JSON result (blueprint + run result)",
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
    blueprint = Blueprint(
        nodes=nodes,
        schema_version="1.1.0",
        metadata={"demo_type": "csv_summary"}
    )

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

    # ------------------------------------------------------------------
    # 6. Optional JSON output dump -------------------------------------
    # ------------------------------------------------------------------
    if args.json_out:
        import json

        payload = {
            "blueprint": json.loads(blueprint.model_dump_json()),
            "run_id": run.run_id,
            "result": json.loads(result.model_dump_json()),
        }

        from pathlib import Path as _Path

        out_path = _Path(args.json_out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nStructured JSON saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
