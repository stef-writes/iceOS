### Dev workflow notes

- Prefer `LLMNodeConfig` terminology throughout code and docs.
- Use `ice new llm-node-tool` to scaffold a minimal tool that mimics a single-prompt LLM behavior if needed.
- Runtime remains executor-only per node type; avoid introducing package-level node implementations.
- Standard commands:
  - `make format` (isort then black), `make format-check`
  - `make lint` (ruff + isort check-only)
  - `make type` (mypy strict)
  - `make test` (pytest with coverage gate)
  - `make audit` (pip-audit)
