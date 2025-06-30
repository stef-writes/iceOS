# CLI Reference

The CLI is built with Typer.  Generate a fresh reference with:

```bash
ice --help > docs/cli_reference.md
```

Current commands snapshot (partial):

```text
Usage: ice [OPTIONS] COMMAND [ARGS]...

iceOS developer CLI

Options:
  --help  Show this message and exit.

Commands:
  init  Initialise an .ice workspace and developer environment
  ls    List tools (shortcut for 'tool ls')
  run   Execute a ScriptChain declared in a Python file
  sdk   Opinionated scaffolds for tools, nodes and chains
  tool  Commands related to tool development
``` 