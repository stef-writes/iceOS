"""Live Seller-Assistant demo – generates listings with OpenAI, formats for
Facebook Marketplace, and POSTs each payload to a locally-spawned mock HTTP
bin so no external marketplace API is contacted.

Prerequisites
-------------
1. `OPENAI_API_KEY` env-var (in .env or shell)
2. FastAPI dev server *not* required; the mock server is started as a Tool
   node inside the workflow.

Run from project root:

```bash
make dev        # optional – starts API, good for blueprint validation
python examples/seller_assistant_live.py
```
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment handling ------------------------------------------------------
# ---------------------------------------------------------------------------

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    fallback_env = Path("config/dev.env.example")
    if fallback_env.is_file():
        load_dotenv(dotenv_path=fallback_env)

# ---------------------------------------------------------------------------
# iceOS imports -------------------------------------------------------------
# ---------------------------------------------------------------------------

import ice_orchestrator  # Import to register executors
from ice_builder.dsl.workflow import WorkflowBuilder
from ice_tools.toolkits.ecommerce import EcommerceToolkit
from ice_core.services import ServiceLocator
from ice_orchestrator.workflow import Workflow as _WF

# Register toolkit with live settings (real OpenAI, no marketplace upload)
EcommerceToolkit(test_mode=False, upload=True).register()

CSV_PATH_DEFAULT = (
    Path("src/ice_tools/toolkits/ecommerce/Supply Yard - Overflow Items - Sheet1.csv").resolve()
)


# ---------------------------------------------------------------------------
# Workflow construction -----------------------------------------------------
# ---------------------------------------------------------------------------

def build_workflow(csv_path: Path) -> _WF:  # type: ignore[name-defined]
    """Construct the end-to-end workflow."""

    builder = WorkflowBuilder("seller_demo_live")

    # Infrastructure node – start mock HTTP bin
    builder.add_tool("mock_server", tool_name="mock_http_bin")

    # Load source data
    builder.add_tool(
        "load_csv",
        tool_name="csv_loader",
        path=str(csv_path),
        delimiter=",",
    )

    # Per-item nodes to be embedded inside the loop
    builder.add_tool(
        "listing_agent",
        tool_name="listing_agent",
        item={"$loop": "item"},
    )
    builder.add_tool(
        "fb_format",
        tool_name="facebook_formatter",
        enriched_product={"$ref": "listing_agent"},
    )
    builder.add_tool(
        "post_item",
        tool_name="api_poster",
        url={"$ref": "mock_server.url"},
        payload={"$ref": "fb_format"},
        mock=True,
    )

    # Grab config objects for embedding
    listing_cfg = next(n for n in builder.nodes if n.id == "listing_agent")
    fb_cfg = next(n for n in builder.nodes if n.id == "fb_format")
    poster_cfg = next(n for n in builder.nodes if n.id == "post_item")

    # Loop over CSV rows
    builder.add_loop(
        "process_loop",
        items_source="load_csv.rows",
        body=[listing_cfg, fb_cfg, poster_cfg],
        item_var="item",
    )

    # Aggregate results
    builder.add_tool(
        "aggregate",
        tool_name="aggregator",
        results={"$ref": "process_loop"},
    )

    # Basic dependency wiring (builder handles most automatically)
    builder.connect("load_csv", "process_loop")

    # Provide Workflow class via DI so MCP validator can instantiate workflows
    ServiceLocator.register("workflow_proto", lambda: _WF)

    wf: _WF = builder.to_workflow(workflow_cls=_WF)  # type: ignore[arg-type]
    wf.validate()
    return wf


# ---------------------------------------------------------------------------
# Main entry-point ----------------------------------------------------------
# ---------------------------------------------------------------------------

async def main() -> None:  # pragma: no cover – example script
    key = os.getenv("OPENAI_API_KEY")
    if not key or not key.startswith("sk-"):
        raise RuntimeError("OPENAI_API_KEY env-var missing or invalid")

    csv_path = Path(os.getenv("CSV_PATH", CSV_PATH_DEFAULT))
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    workflow = build_workflow(csv_path)

    print("Executing workflow… (OpenAI calls per row; posting to local mock server)")
    result = await workflow.execute()

    aggregate_out = result.output.get("aggregate", {})  # type: ignore[index]
    print("\n=== Aggregated Listing Data ===")
    pprint(aggregate_out)

    # Persist mock postings --------------------------------------------
    try:
        mock_url = result.output.get("mock_server", {}).get("url")  # type: ignore[index]
        if mock_url:
            import httpx, json as _json
            postings = httpx.get(mock_url, timeout=5).json()
            out_dir = Path(__file__).parent / "output"
            out_dir.mkdir(exist_ok=True)
            out_file = out_dir / "listings_live.json"
            out_file.write_text(_json.dumps(postings, indent=2))
            print(f"\n📄 Mock postings written to {out_file.relative_to(Path.cwd())}")
            print(f"🔗 Browse live at {mock_url}")
    except Exception as e:
        print(f"(Could not fetch/write mock postings: {e})")


if __name__ == "__main__":
    asyncio.run(main())
