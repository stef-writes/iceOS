# ice_cli – Command-Line Interface for iceOS

`ice` is the primary developer tool for interacting with a running iceOS stack.
It wraps the REST / WebSocket API and local helpers so you can push, run and
inspect workflows without writing scripts.

```
$ ice --help
Commands:
  push          Upload a Blueprint JSON file
  run           Start an execution and stream output
  list          List tools, blueprints, executions
  doctor        Run repo health-checks (lint, type, test)
  network …     Forward to runtime network sub-commands
```

## Installation
```
poetry install --with dev     # or pip install -e .
```
The `ice` entry-point is installed via the `ice_cli.cli:cli` Typer app.

## Scaffolder quick-start
Generate fully-typed components without manual boiler-plate:

```bash
# Create a deterministic tool
ice new tool pricing_calc_tool --description "Compute sale price"

# Create an agent and expose it as a tool
ice new agent support_chat_agent --system-prompt "You are support." --tools search_tool
ice new agent-tool support_chat_agent

# Stateless LLM operator (single-shot generation)
ice new llm-operator summarize_text --model gpt-4o
```

Each command writes to `src/ice_tools/generated/…` and components auto-register on import – no extra wiring required.

## Typical workflow
```bash
make dev-up                  # start Redis & API in background

# Build a Blueprint with the SDK or Frosty
python examples/hello_workflow.py > hello.json

# Upload and execute
ice push hello.json          # prints Blueprint ID and stores it locally
ice run --last               # streams execution status until completion
```

## Environment variables
| Variable          | Description                                | Default                    |
|-------------------|--------------------------------------------|----------------------------|
| `ICEOS_API_URL`   | Base URL for the iceOS API                 | `http://localhost:8000`    |
| `ICEOS_API_TOKEN` | Bearer token (once auth middleware added)  | *not required in dev mode* |

## Developer notes
* `ice_cli` **only** imports from `ice_core` for shared models and uses
  `httpx` for network calls – no cross-layer violations.
* New sub-commands should live in `src/ice_cli/commands/` and be registered
  in `ice_cli.cli` to keep the main entry-point lean.
