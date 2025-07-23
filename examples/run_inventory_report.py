import json
import time
from pathlib import Path

import httpx

API_URL = "http://localhost:8000"
BLUEPRINT_FILE = Path(__file__).with_name("inventory_report_blueprint.json")


def main() -> None:
    bp_json = json.loads(BLUEPRINT_FILE.read_text())

    # 1. Register / upsert blueprint -----------------------------------
    resp = httpx.post(f"{API_URL}/api/v1/mcp/blueprints", json=bp_json, timeout=10)
    resp.raise_for_status()
    bp_id = resp.json()["blueprint_id"]
    print(f"Blueprint registered as {bp_id}")

    # 2. Start run (inline blueprint for simplicity) -------------------
    run_req = {"blueprint": bp_json, "options": {"max_parallel": 2}}
    resp = httpx.post(f"{API_URL}/api/v1/mcp/runs", json=run_req, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    run_id = data["run_id"]
    status_url = f"{API_URL}{data['status_endpoint']}"
    print(f"Run started: {run_id}")

    # 3. Poll for result -----------------------------------------------
    while True:
        r = httpx.get(status_url, timeout=10)
        if r.status_code == 202:
            print("…still running")
            time.sleep(2)
            continue
        r.raise_for_status()
        result = r.json()
        break

    if not result["success"]:
        raise SystemExit(f"Run failed: {result['error']}")

    html = result["output"].get("rendered", "")
    out_path = Path("report.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written to {out_path.resolve()}")


if __name__ == "__main__":
    main() 