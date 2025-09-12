from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import httpx


def load_yaml(path: Path) -> Dict[str, Any]:
    import yaml  # type: ignore

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: import_bundle.py <bundle_dir> <agent_name>")
        sys.exit(2)
    bundle_dir = Path(sys.argv[1]).resolve()
    agent_name = sys.argv[2]

    bundle = load_yaml(bundle_dir / "bundle.yaml")
    workflows = bundle.get("workflows", {})
    entry = bundle.get("entrypoint")
    if not isinstance(workflows, dict) or not entry:
        raise SystemExit("invalid bundle: missing workflows or entrypoint")
    if entry not in (f"chatkit.{k}" for k in workflows.keys()):
        # proceed best-effort; we only need a path
        pass
    # read workflow yaml
    wf_rel = workflows.get(entry.split(".")[-1])
    if not wf_rel:
        raise SystemExit("entrypoint not found in workflows map")
    wf = load_yaml((bundle_dir / wf_rel).resolve())

    base = os.getenv("BASE", "http://localhost:8000")
    token = os.getenv("ICE_API_TOKEN", "REPLACE_ME_STRONG_RANDOM_TOKEN")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1) register agent definition (lightweight) so AgentNodeConfig.package resolves
    agent_def = {
        "type": "agent",
        "name": agent_name,
        "description": f"Agent {agent_name}",
        "agent_system_prompt": (wf.get("metadata", {}) or {}).get("draft_name", "Agent"),
        "agent_tools": ["writer_tool"],
        "agent_llm_config": {"provider": "openai", "model": "gpt-4o"},
        "auto_register": True,
    }

    with httpx.Client(timeout=25) as c:
        r = c.post(f"{base}/api/mcp/components/validate", headers=headers, json=agent_def)
        if r.status_code >= 300:
            print("validate agent failed", r.status_code, r.text)
            sys.exit(1)
        # register to ensure availability immediately
        r = c.post(f"{base}/api/mcp/components/register", headers=headers, json=agent_def)
        if r.status_code >= 300:
            print("register agent failed", r.status_code, r.text)
            sys.exit(1)

        # 2) create blueprint (inline wf converted to MCP Blueprint shape)
        # wf already matches MCP Blueprint shape: schema_version/metadata/nodes
        bp = {
            "schema_version": wf.get("schema_version", "1.2.0"),
            "nodes": wf["nodes"],
            "metadata": wf.get("metadata", {}),
        }
        r = c.post(f"{base}/api/mcp/blueprints", headers=headers, json=bp)
        if r.status_code not in (200, 201):
            print("blueprint create failed", r.status_code, r.text)
            sys.exit(1)
        ack = r.json()
        bp_id = ack.get("blueprint_id")
        print("BLUEPRINT", bp_id)

        # 3) execute once to verify
        run_req = {"blueprint_id": bp_id}
        r = c.post(f"{base}/api/mcp/runs", headers=headers, json=run_req)
        print("RUN", r.status_code, r.text[:240])


if __name__ == "__main__":
    main()


