## Plugins, CapabilityKits, Bundles – Architecture and Migration Guide

This document is the single source of truth for how extensibility works in iceOS. It defines terms, success criteria, directory structure, naming conventions, initialization, and an exact migration plan from the current layout to the final end-state.

### Definitions (canonical)

- Plugins: The umbrella namespace that contains every user-extensible asset. Plugins are versioned, testable, and load via manifests.
- CapabilityKits (Kits): Reusable capabilities implemented as Tools. Tools are the only place where side effects (network, DB, filesystem) occur.
- Bundles: Customer-facing packaged “apps” or workflows that compose Tools from Kits. Bundles define entry workflows, presets, and optional UI schemas.
- Connectors (a subtype of Kits): CapabilityKits that integrate with third-party systems (e.g., Google, GitHub). They are gated by optional dependencies and credentials.

### Success criteria (100% done)

- Only two top-level Plugin concepts exist: CapabilityKits and Bundles. No aliases, no shims.
- Side-effects live exclusively inside Tools; Nodes/Agents/Workflows remain declarative and typed.
- All plugin sources live under `plugins/`; all build artifacts live under `dist/`.
- Manifests are loaded solely via `ICEOS_PLUGIN_MANIFESTS` (comma-separated absolute paths). No manual registration scripts remain.
- ChatKit ships as a Bundle with `entrypoint=chatkit.rag_chat`; it runs end-to-end via CLI and API.
- Two foundational CapabilityKits exist (memory, search). One minimal Connector (Gmail) is provisioned or stubbed with import guards.
- CI builds once and runs type, unit, and integration tests; the test image imports a writer tool from the new Plugins namespace. All green from scratch.

### Final end-state layout (SSOT)

```
plugins/
  bundles/
    chatkit/
      bundle.yaml
      workflows/
        rag_chat.yaml
      presets/
        system_prompt_default.txt
        llm_openai_gpt4o.json
      ui/
        form_schema.json
      examples/
        tiny_docs.md

  kits/
    tools/
      memory/
        ingestion_tool.py
        memory_search_tool.py
        memory_write_tool.py
        recent_session_tool.py
        memory_summarize_tool.py
        plugins.v0.yaml
      search/
        search_tool.py
        lookup_tool.py
        writer_tool.py
        plugins.v0.yaml

    connectors/   # optional in launch; can start with one minimal
      google/
        gmail/
          gmail_search_messages_tool.py
          # gmail_send_message_tool.py (optional)
          plugins.v0.yaml

dist/
  bundles/
    chatkit-1.0.0.ice.tgz     # built artifacts

src/                         # runtime, APIs, orchestrator (unchanged)
scripts/
  ops/                        # diagnostics only, not imported by src
  maintenance/                # maintenance utilities
examples/
docs/
```

### Naming and imports (descriptive, unambiguous)

- Tool modules and classes:
  - `plugins.kits.tools.memory.memory_search_tool.MemorySearchTool`
  - `plugins.kits.connectors.google.gmail.gmail_search_messages_tool.GmailSearchMessagesTool`
- Bundle ID: `chatkit.rag_chat` (used as the `blueprint_id` in API calls)
- File names are explicit (e.g., `gmail_search_messages_tool.py`, `memory_summarize_tool.py`).

### Initialization

- Environment variable loads manifests (comma-separated):
  ```
  ICEOS_PLUGIN_MANIFESTS=/app/plugins/kits/tools/memory/plugins.v0.yaml,/app/plugins/kits/tools/search/plugins.v0.yaml[/app/plugins/kits/connectors/google/gmail/plugins.v0.yaml]
  ```
- Dockerfile copies `plugins/` into the image as `/app/plugins`; Compose sets `ICEOS_PLUGIN_MANIFESTS` to those paths. No registry bootstrap scripts.

### Running ChatKit

- CLI (example):
  ```
  ice bundle run chatkit \
    --file examples/user_assets/resume.txt \
    --note "focus skills" \
    --query "Summarize me" \
    --session s1 \
    --model gpt-4o
  ```
- API:
  ```json
  {
    "blueprint_id": "chatkit.rag_chat",
    "inputs": {
      "query": "Summarize me",
      "org_id": "demo_org",
      "user_id": "demo_user",
      "session_id": "s1",
      "system_prompt": "",
      "model": "gpt-4o",
      "temperature": 0.2,
      "top_p": 0.95,
      "max_tokens": 512
    }
  }
  ```

### ConnectorKits (example: Gmail)

- Minimal tool: `gmail_search_messages_tool.py`
  - Inputs: `query: str`, `label_ids: list[str] | None`, `max_results: int = 10`
  - Outputs: `messages: list[{id: str, snippet: str, headers: dict}]`
  - Guarded by optional extras and env credentials (e.g., `GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN`); tests use `pytest.importorskip` if extras are missing.
- Manifest: `plugins/kits/connectors/google/gmail/plugins.v0.yaml` lists the connector tools.

### CI / Tests

- Dockerfile (test stage) imports `plugins.kits.tools.search.writer_tool:create_writer_tool` for the bootstrap.
- Integration tests set `ICEOS_PLUGIN_MANIFESTS` to Plugins manifests; no references to old paths remain.
- Nightly/optional lanes can include connector suites; PR CI remains fast and green.

### Migration plan (exact steps)

1) Create new structure under `plugins/` and `dist/`.
2) Move Kits:
   - `capability_kits/memory/*` → `plugins/kits/tools/memory/`
   - `capability_kits/search/*` → `plugins/kits/tools/search/`
   - Update both `plugins.v0.yaml` files to use the `plugins.kits.tools.*` import paths.
3) Move Bundle:
   - `chatkit/*` → `plugins/bundles/chatkit/`
   - Ensure `bundle.yaml` and `workflows/rag_chat.yaml` exist and inputs/outputs match docs.
4) Update initialization:
   - Dockerfile: `COPY Plugins /app/plugins`
   - Compose/tests/src fallbacks: set `ICEOS_PLUGIN_MANIFESTS` to the two (or three, with connector) manifest paths under `plugins/`.
5) Purge old references and folders:
   - Remove any `packs.*`, `toolkits/*`, `capability_packs/*` imports/paths.
   - Delete legacy folders after references are green.
6) Rebuild from scratch:
   - `docker build --no-cache --pull --target api ...`
   - `docker build --no-cache --pull --target test ...`
   - `make ci` and `make ci-integration`
7) Update docs (Quickstart + Launch Plan) to reference ChatKit Bundle and `plugins/` manifests.
8) Optional: Add `Plugins/kits/connectors/google/gmail/` with the minimal search tool and manifest; gate via extras and skip tests if credentials missing.

### Mapping from current → final

```
capability_kits/memory/*      → plugins/kits/tools/memory/*
capability_kits/search/*      → plugins/kits/tools/search/*
chatkit/*                     → plugins/bundles/chatkit/*
docker-compose[.itest].yml    → ICEOS_PLUGIN_MANIFESTS=/app/plugins/kits/tools/memory/plugins.v0.yaml,/app/plugins/kits/tools/search/plugins.v0.yaml
Dockerfile (api/test)         → COPY Plugins /app/plugins; test bootstrap imports writer_tool from plugins namespace
tests/*                       → load manifests from Plugins paths; no packs/toolkits/capability_packs
scripts/examples/run_rag_chat → removed (use ChatKit Bundle run)
scripts/register_new_tools    → removed (manifests auto-load)
scripts/bootstrap_registry... → removed (manifests auto-load)
scripts/verify_runtime        → scripts/ops/verify_runtime.py (ops-only)
```

### Guardrails and non-goals

- No deprecation shims, no aliases. We make a clean, one-time move.
- `src/` must not import from `plugins/` directly; all cross-layer calls go through the registry via manifests.
- Long, explicit names are preferred for clarity over brevity.

### Rationale and strategy

This mirrors proven marketplace architectures (Zapier/Make/n8n): small, reusable capabilities (Tools) and productized Bundles for end users. It keeps the runtime deterministic, simplifies packaging and governance, and positions iceOS for third‑party ecosystems.
