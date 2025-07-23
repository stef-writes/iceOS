import json
import os
from pathlib import Path

import httpx

API_URL = "http://localhost:8000"

# Ensure server running reminder ------------------------------------------------
print("⏳  Ensure `uvicorn src.ice_api.main:app --port 8000` is running in another terminal.")

# Step 1 – Upload blueprint using chain reference ------------------------------
blueprint_path = Path(__file__).with_name("inventory_report_blueprint_chain.json")
blueprint_payload = json.loads(blueprint_path.read_text())

run_req = {"blueprint": blueprint_payload, "options": {"max_parallel": 2}}

with httpx.Client(timeout=60.0) as client:
    # Kick off run -------------------------------------------------------------
    resp = client.post(f"{API_URL}/api/v1/mcp/runs", json=run_req)
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"▶️  Run started: {run_id}")

    # Poll for completion -----------------------------------------------------
    result_url = f"{API_URL}/api/v1/mcp/runs/{run_id}"
    while True:
        r = client.get(result_url)
        if r.status_code == 202:
            print("   … still running …")
            import time; time.sleep(2)
            continue
        r.raise_for_status()
        body = r.json()
        break

print("✅  Workflow finished")
print(json.dumps(body, indent=2)[:400] + "…")

# Write HTML report ------------------------------------------------------------
html = body.get("output", {}).get("html") or body.get("output", {}).get("rendered")
if html:
    out_path = Path("report.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"🔖  HTML report written to {out_path.absolute()}")
else:
    print("⚠️  No HTML output found") 