# ice CLI Overview

The `ice` command is a Typer-based developer tool.

Key commands:

* `ice init <project>` – scaffold a new repo
* `ice run <file.chain.py>` – execute chain locally
* `ice run-remote --blueprint <bp.json>` – hit remote MCP endpoint
* `ice doctor` – lint + test + type + security checks

CLI never touches internals directly; it goes through `ice_sdk` APIs. 