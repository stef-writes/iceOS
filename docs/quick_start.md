# Quick Start

```bash
# 1. Clone & install
poetry install --with dev

# 2. Run unit tests & quality gate
make doctor

# 3. Launch FastAPI server (auto-reload)
make dev

# 4. Call the health-check
curl http://localhost:8000/health

# 5. Run a trivial chain via CLI
ice chain run examples/echo_chain.json
```

For a deeper dive into ScriptChain and node configuration see the **Core Concepts** section. 