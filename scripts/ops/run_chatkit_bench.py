#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import httpx


def run_once(base_url: str, token: str, query: str, session_id: str) -> Dict[str, Any]:
    payload = {
        "blueprint_id": "chatkit.rag_chat",
        "inputs": {
            "query": query,
            "org_id": "bench_org",
            "user_id": "bench_user",
            "session_id": session_id,
        },
    }
    with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as c:
        t0 = time.perf_counter()
        r = c.post(
            f"{base_url.rstrip('/')}/api/v1/executions/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        exec_id = r.json()["execution_id"]

        # Poll
        while True:
            st = c.get(
                f"{base_url.rstrip('/')}/api/v1/executions/{exec_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            st.raise_for_status()
            data = st.json()
            if data.get("status") in {"completed", "failed"}:
                break
            time.sleep(0.1)
        t1 = time.perf_counter()

    return {
        "status": data.get("status"),
        "latency_sec": round(t1 - t0, 3),
        "result": data.get("result", {}),
        "events": data.get("events", []),
    }


def main() -> None:
    base_url = os.getenv("ICE_API_URL", "http://localhost")
    token = os.getenv("ICE_API_TOKEN", "dev-token")
    query = os.getenv("BENCH_QUERY", "Summarize me")
    warmups = int(os.getenv("BENCH_WARMUPS", "1"))
    runs = int(os.getenv("BENCH_RUNS", "3"))

    # Optional: deterministic embeddings for CI/demo
    os.environ.setdefault("ICEOS_EMBEDDINGS_PROVIDER", "hash")

    results = []
    # Warmups
    for i in range(warmups):
        _ = run_once(base_url, token, query, session_id=f"bench_warm_{i}")

    # Measured
    for i in range(runs):
        res = run_once(base_url, token, query, session_id=f"bench_{i}")
        results.append(res)

    latencies = [r["latency_sec"] for r in results]
    p50 = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
    summary = {
        "runs": runs,
        "p50_latency_sec": p50,
        "avg_latency_sec": round(sum(latencies) / max(1, len(latencies)), 3),
        "details": results,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
