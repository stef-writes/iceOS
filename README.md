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
