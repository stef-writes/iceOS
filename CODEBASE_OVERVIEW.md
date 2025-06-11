# Codebase Overview (auto-generated)

> Last updated: 2025-06-11 – run `make refresh-docs` to regenerate.

## Packages

- **`src/ice_sdk`** – Core SDK: base abstractions (`BaseNode`, `BaseTool`) and runtime glue.
- **`src/schemas`** – Pydantic models shared across SDK & App layers.
- **`src/app`** – Reference application built on the SDK.
  - **`app.agents`** – Pre-configured `Agent` classes ready for orchestration.
  - **`app.chains`** – Modular, reusable Chains combining Tools & Nodes.
  - **`app.nodes`** – Domain-specific compute Nodes (pure, side-effect-free).
  - **`app.tools`** – Side-effecting Tools (DB, HTTP, FS, etc.).
  - **`app.event_sources`** – External triggers: webhooks, CRON, message queues.
  - **`app.services`** – Stateless helpers (vector search, cache, etc.).
  - **`app.api`** – FastAPI powered REST endpoints.
  - **`app.utils`** – Generic utility helpers.
  - **`app.data`** – Sample datasets & fixtures.
  - **`app.llm_providers`** – Wrappers for OpenAI, Anthropic, etc.
  - **`app.templates`** – Jinja / prompt templates used by Chains.

## Key Classes (high-level)

| Class | Module | Purpose |
| ----- | ------ | ------- |
| `BaseNode` | `ice_sdk.base_node` | Async computation unit with typed IO. |
| `BaseTool` | `ice_sdk.base_tool` | Gateway for external side-effects. |
| `ToolService` | `ice_sdk.tool_service` | Runtime registry & executor for Tools. |
| `MainApp` | `app.main` | Entrypoint wiring config & CLI. |

For full capability list, see `CAPABILITY_CATALOG.json`. 