Project setup and live verification
==================================

Prerequisites
- Python 3.10
- Poetry

Install
- poetry install --with dev

Environment
- Export provider keys as needed:
  - OPENAI_API_KEY=...
  - SERPAPI_KEY=...

Run live verification (real LLM + SerpAPI when keys set)
- make verify-live

What it does
- Executes these flows using real providers:
  - LLM-only (prompt rendering → provider)
  - LLM → Tool (writer_tool)
  - LLM1 → LLM2 (dependency context propagation)
  - Agent → Tool (AgentRuntime plan→act)

Notes
- Tests default to deterministic mode; API E2E tests can be gated to live later via an env flag (e.g., ICE_LIVE=1).
- Lint/type/test:
  - make lint
  - make type
  - make test

Troubleshooting
- If OpenAI errors reference httpx proxies arg, ensure the active environment has httpx==0.24.1 and openai==1.14.1.
- If SearchTool returns fallback, check SERPAPI_KEY is exported.