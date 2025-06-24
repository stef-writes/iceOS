# iceOS v1 – Intelligent Composable Environment

[![CI](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml/badge.svg)](https://github.com/stef-writes/iceOSv1-A-/actions/workflows/ci.yml)

> **iceOS** is an open-source operating layer for building agentic, event-driven AI applications.

---

## Quick Start

```bash
# Clone & enter repo
$ git clone https://github.com/stef-writes/iceOSv1-A-.git && cd iceOSv1-A-

# Create virtual-env and install deps
$ python -m venv .venv && source .venv/bin/activate
$ pip install -e .[dev]

# Run the test suite (≈2s)
$ make test
```

---

### Common Tasks
| Task                | Command                 |
|---------------------|-------------------------|
| Lint & type-check   | `make lint`             |
| Remove artefacts    | `make clean`            |
| Generate docs       | `make refresh-docs`     |
| Run a workflow demo | `python scripts/demo_run_chain.py` |

---

## 📚 Further Reading
The extended architecture overview, feature list, and roadmap have moved to:

* `docs/vision_and_moats.md`
* `docs/roadmap_agile.md`
* `docs/archive/README_legacy.md` (full legacy README)

---

This trimmed README keeps the surface light and forward-looking while detailed design docs live under `docs/`. 🎉

## 🔐 Security
`ice_sdk.tools.mcp` now supports optional Fernet-encrypted transport. To enable, pass an `encryption_key` (32-byte URL-safe base64) in the MCP server parameters:

```python
server = MCPServerStdio({
    "command": "myserver",
    "args": ["--stdio"],
    "encryption_key": os.environ["MCP_FERNET_KEY"],
})
```

If `cryptography` is not installed the call silently falls back to plaintext. Install the extra via Poetry or pip:

```bash
# Poetry
poetry add cryptography

# pip
pip install cryptography
```

❗  For production environments we strongly recommend supplying a key and confirming that the dependency is available to ensure confidentiality.
