## Experiments & Demos

This guide leads with real user activities. Part 1 uses built‑ins to get moving fast; Part 2 focuses on building from scratch; Part 3 is a capability checklist to validate knobs and UX.

### Part 1 — Built‑in plugins (fast wins)

- RAG ChatKit bundle
  - Ingest example assets → run `chatkit.rag_chat` via `IceClient.run_bundle` (YAML fallback) and via registered id.
  - Vary prompt/temperature for summaries.
- Search tool (e.g., SerpAPI) + LLM
  - Install key → run LLM → search → LLM chain using provided tool.

### Part 2 — Build from scratch (user‑owned assets)

1) Custom Tool → Workflow
   - Write a Python Tool (e.g., `csv_loader`), validate+register.
   - Compose a blueprint: tool → LLM; run by id via REST.

2) Multi‑step stateless LLM workflow
   - Create a 3–5 node LLM chain (reasoning steps or “adapt blog for LinkedIn/Twitter”).
   - Tune per‑node prompts and temperatures; run and compare outputs.

3) Custom Agent with memory & knowledge
   - Compose an agent with custom `system_prompt`, custom memory policy (what to retain), and knowledge docs (semantic memory).
   - Verify multi‑turn conversation continuity via `session_id` + retrieval.

4) Assemble a new workflow from your Library
   - Pull pre‑existing user assets (tools/agents/workflows) from the Library API.
   - Construct a brand‑new workflow primarily from reusable components; register and run.

Suggested scripts/targets:
- `scripts/demos/tool_from_scratch.py`, `scripts/demos/multillm_workflow.py`, `scripts/demos/agent_with_memory.py`, `scripts/demos/library_composition.py`
- Make: `demo-tool`, `demo-llm`, `demo-agent`, `demo-compose`

### Part 3 — Capability drills (knobs & UX)

- LLM prompt editing: modify `node.prompt`, rerun.
- Agent `system_prompt` override: compose/patch agent and re‑run.
- Temperature/top_p adjustments: set `LLMConfig.temperature`/`top_p` and compare.
- Inline vs registered vs bundle:
  - `IceClient.run(blueprint=...)`
  - `POST /api/v1/blueprints` → `/api/v1/executions`
  - `IceClient.run_bundle(id, blueprint_yaml_path=...)`
- MCP partial blueprints: create → update (X‑Version‑Lock) → suggest → finalize.
- Memory drills: `memory_write_tool`, `memory_search_tool`, session memory; RBAC isolation (cross‑org denied).
- Repository browsing: `GET /api/v1/library/assets/index` and `IceClient.list_library`.
- Provider matrix: echo fallback vs OpenAI/Anthropic/DeepSeek (keys); expected failure modes.
