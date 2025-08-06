# ice_cli – Command-Line Interface for iceOS

`ice_cli` exposes a **single entry-point executable** named `ice` that wraps
common developer workflows: scaffolding, running blueprints, exporting JSON
schemas, and pushing workflows to the API layer.

```
$ ice --help
Usage: ice [OPTIONS] COMMAND [ARGS]...

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  export-schemas  Dump all JSON Schemas under schemas/generated/
  new             Scaffold new project components (tools/agents/workflows)
  push            Upload blueprint/workflow JSON to remote ice_api
  run             Execute a blueprint YAML locally
```

Implementation lives in `src/ice_cli/commands/*.py` and uses **Click** – no
additional runtime dependencies.

---

## 1. Scaffolding quick-start

```bash
# Generate a new Tool skeleton in src/acme_tools/
$ ice new tool --name acme_discount --description "Apply ACME discount" --output-dir src/acme_tools

# Resulting files:
#   src/acme_tools/acme_discount.py
#   tests/unit/acme_tools/test_acme_discount.py
```

Other scaffold sub-commands: `agent`, `agent-tool`, `llm-operator`.

---

## 2. Running a blueprint

```bash
# Execute in offline/test mode (default)
$ ice run examples/blueprints/seller_assistant.yaml

# Live mode
$ ICE_TEST_MODE=0 ice run examples/blueprints/seller_assistant.yaml
```

`ice run` internally calls `ice_builder` to parse YAML → `Workflow` and then
hands execution to `ice_orchestrator`.

---

## 3. Exporting JSON-Schemas

```bash
$ ice export-schemas
# Schemas written to schemas/generated/* (used by backend validator)
```

---

## Development notes

* CLI startup must stay under **100 ms** (cold) – avoid heavy imports.
* All commands defer to underlying packages; `ice_cli` itself holds **no
  business logic**.
* Integration tests live in `tests/unit/ice_cli/*`.
