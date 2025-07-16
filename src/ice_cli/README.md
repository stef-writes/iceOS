# ice_cli – Command-Line Interface

## Overview
The `ice` command offers a friendly shell for creating, running and analysing
ScriptChains locally or against a remote MCP.

Built with **Typer**, it re-uses only the **public SDK APIs** – no private
imports allowed.

### Key Commands
| Command | Description |
|---------|-------------|
| `ice init <project>`      | Scaffold a repo with recommended layout |
| `ice run <file.chain.py>` | Execute chain locally (async)          |
| `ice doctor`              | Lint, type-check, run tests, security  |
| `ice update`              | Upgrade deps & regenerate lockfile     |

## Example
```bash
ice init my-bot
cd my-bot
ice run greeting.chain.py --input '{"name":"Ada"}'
```

## Development
```bash
# run CLI unit tests
pytest tests/cli
```

## Layer Contract
* **Never** import from `ice_api.*`, `ice_orchestrator.*` or `app.*`
  directly – always go through `ice_sdk`.
* Long-running tasks must use `async/await`; avoid blocking the event loop.

## License
MIT. 