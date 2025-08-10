Project setup and live verification
==================================

Prerequisites
- Python 3.10
- Poetry 2.x

Install
- poetry install --with dev --no-interaction

Environment
- Export provider keys as needed:
  - OPENAI_API_KEY=...
  - SERPAPI_KEY=...
  - Optionally set ICE_LIVE=1 to gate live API tests in the future

Run live verification (real LLM + SerpAPI when keys set)
- make verify-live

What it does
- Executes these flows using real providers:
  - LLM-only (prompt rendering → provider)
  - LLM → Tool (writer_tool)
  - LLM → SearchTool → LLM (SerpAPI + OpenAI)
  - LLM1 → LLM2 (dependency context propagation)
  - Agent → Tool (AgentRuntime plan→act; intra-run memory)
  - Swarm (simple factory)

Notes
- Tests default to deterministic mode; API E2E tests can be gated to live later via an env flag (e.g., ICE_LIVE=1).
- Lint/type/test:
  - make lint
  - make type
  - make test
  - make audit (optional dependency vulnerability scan)

Troubleshooting
- If OpenAI errors reference httpx proxies arg, ensure the active environment has httpx==0.24.1 and openai==1.14.1.
- If SearchTool returns fallback, check SERPAPI_KEY is exported.
- If swarm fails on missing agents, ensure factories are registered (see scripts/verify_runtime.py).