"""Run the seller-assistant workflow against OpenAI for real title/description generation
and **skip** the marketplace upload.  Requires a valid `OPENAI_API_KEY` env-var.

Usage (from project root):

```bash
export OPENAI_API_KEY="<your-key>"
poetry run python examples/seller_assistant_live.py
```

This keeps all network traffic limited to the OpenAI call; no external
marketplace API is contacted because `upload=False`.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from pprint import pprint

from ice_builder.dsl.workflow import WorkflowBuilder
from ice_core.services import ServiceLocator
from ice_orchestrator.workflow import Workflow as _WF

CSV_PATH_DEFAULT = (
    Path("src/ice_tools/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
)


def build_workflow(csv_path: Path) -> _WF:  # type: ignore[name-defined]
    builder = WorkflowBuilder("seller_demo_live")

    builder.add_tool(
        "load_csv",
        tool_name="csv_loader",
        path=str(csv_path),
        delimiter=",",
    )

    builder.add_loop(
        "process_loop",
        items_source="load_csv.rows",
        body_nodes=["listing_agent"],
        item_var="item",
    )

    builder.add_tool(
        "listing_agent",
        tool_name="listing_agent",
        margin_percent=25.0,
        model="gpt-4o",
        test_mode=False,  # Real OpenAI call
        upload=False,  # <-- Skip marketplace upload
    )

    builder.add_tool(
        "aggregate",
        tool_name="aggregator",
        results="{{ process_loop.* }}",
    )

    # Wire dependencies -----------------------------------------------------
    builder.connect("load_csv", "process_loop")
    builder.connect("process_loop", "listing_agent")
    builder.connect("process_loop", "aggregate")

    # DI hook – resolve Workflow class without direct import across layers
    ServiceLocator.register("workflow_proto", lambda: _WF)

    wf: _WF = builder.to_workflow()  # type: ignore[arg-type]
    wf.validate()
    return wf


async def main() -> None:  # pragma: no cover – example script
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.startswith("sk-"):
        raise RuntimeError("OPENAI_API_KEY env-var missing or invalid")

    csv_path = Path(os.getenv("CSV_PATH", CSV_PATH_DEFAULT))
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    workflow = build_workflow(csv_path)
    print("Executing workflow… (this will call OpenAI once per row, no marketplace upload)")
    result = await workflow.execute()

    aggregate_out = result.output.get("aggregate", {})  # type: ignore[index]
    print("\n=== Aggregated Listing Data ===")
    pprint(aggregate_out)


if __name__ == "__main__":
    asyncio.run(main())
