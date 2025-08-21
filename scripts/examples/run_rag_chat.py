from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Mapping

import httpx

from ice_client.client import IceClient
from packs.first_party_agents.rag_agent import rag_chat_blueprint_agent


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="RAG chat demo: ingest knowledge and run a scoped query"
    )
    p.add_argument("--query", default="What is the capital of France?")
    p.add_argument("--org", default=os.getenv("ICE_DEFAULT_ORG_ID", "demo_org"))
    p.add_argument("--user", default=os.getenv("ICE_DEFAULT_USER_ID", "demo_user"))
    p.add_argument("--scope", default="kb")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--model", default=os.getenv("ICEOS_LLM_MODEL", "gpt-4o"))
    p.add_argument(
        "--source-type",
        choices=["url", "file", "text"],
        default="text",
        help="Ingestion source type",
    )
    p.add_argument("--source", default="Paris is the capital of France.")
    p.add_argument("--chunk-size", type=int, default=1000)
    p.add_argument("--overlap", type=int, default=200)
    p.add_argument(
        "--mode",
        choices=["ingest", "query", "both", "dry-run"],
        default="both",
    )
    p.add_argument("--with-citations", action="store_true")
    p.add_argument("--debug-retrieval", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--hash-embedder", action="store_true")
    p.add_argument("--session-id", default="demo_session")
    # New: optional file inputs and style/tone hints
    p.add_argument("--files", default="", help="Comma-separated text files to ingest")
    p.add_argument("--style", default="concise")
    p.add_argument("--tone", default="neutral")
    return p.parse_args()


def _split_files(raw: str) -> list[Path]:
    return [Path(p.strip()) for p in raw.split(",") if p.strip()] if raw.strip() else []


async def _ingest(client: IceClient, ns: argparse.Namespace) -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "tool:ingestion_tool",
            "arguments": {
                "inputs": {
                    "source_type": ns.source_type,
                    "source": ns.source,
                    "scope": ns.scope,
                    "chunk_size": ns.chunk_size,
                    "overlap": ns.overlap,
                    "org_id": ns.org,
                    "user_id": ns.user,
                }
            },
        },
    }
    # If file list provided, override source_type/source per file
    files = _split_files(ns.files)
    if files:
        for fp in files:
            text = fp.read_text(encoding="utf-8")
            payload["params"]["arguments"]["inputs"].update(
                {
                    "source_type": "text",
                    "source": text,
                    "filename": fp.name,
                }
            )
            resp = await client._client.post("/api/v1/mcp/", json=payload)
            resp.raise_for_status()
        return
    # Fallback: single source from args
    resp = await client._client.post("/api/v1/mcp/", json=payload)
    resp.raise_for_status()


async def main() -> None:
    ns = _args()
    base_url = os.getenv("ICE_API_URL", "http://localhost:8000")
    token = os.getenv("ICE_API_TOKEN", "dev-token")

    if ns.debug_retrieval:
        os.environ["ICE_DEBUG_RETRIEVAL"] = "1"
    if ns.hash_embedder:
        os.environ["ICEOS_EMBEDDINGS_PROVIDER"] = "hash"

    # Use network transport by default
    transport: httpx.AsyncBaseTransport | None = None

    async with IceClient(base_url, auth_token=token, transport=transport) as client:
        if ns.mode in ("ingest", "both"):
            await _ingest(client, ns)
            if ns.mode == "ingest":
                print("Ingestion completed.")
                return

        if ns.mode == "dry-run":
            print("Dry run: no query executed.")
            return

        # Build RAG chat blueprint via first-party agent
        bp = rag_chat_blueprint_agent(
            model=ns.model,
            scope=ns.scope,
            top_k=ns.top_k,
            with_citations=ns.with_citations,
        )

        # Execute with explicit inputs
        exec_id = await client.run(
            blueprint=bp,
            inputs={
                "query": ns.query,
                "org_id": ns.org,
                "user_id": ns.user,
                "session_id": ns.session_id,
                "style": ns.style,
                "tone": ns.tone,
            },
        )
        final = await client.poll_until_complete(exec_id, timeout=60)
        out: Mapping[str, Any] = final

        if ns.as_json:
            print(json.dumps(out, indent=2))
            return

        # Human-readable summary
        print(f"Org/User: {ns.org}/{ns.user}  Scope: {ns.scope}  TopK: {ns.top_k}")
        try:
            llm_out = out.get("result", {}).get("output", {}).get("llm", {})
            print(
                "\nAssistant ("
                + ns.tone
                + ", "
                + ns.style
                + "):\n"
                + str(llm_out.get("response", llm_out.get("text", ""))).strip()
            )
        except Exception:
            pass
        if ns.debug_retrieval:
            try:
                search_out = out.get("result", {}).get("output", {}).get("search", {})
                dbg = search_out.get("debug") or []
                if dbg:
                    print("\nRetrieved (key, score):")
                    for item in dbg[: ns.top_k]:
                        print(
                            f"- {item.get('key')}  ({item.get('cosine_similarity'):.3f})"
                        )
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
