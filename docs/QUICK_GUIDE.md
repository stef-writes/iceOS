# iceOS Quick Guide ⭐️

This guide helps you get started with iceOS quickly. Choose your path:

## 🚀 Quick Start (5 minutes)

1. **Setup Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API Keys**
   ```bash
   export OPENAI_API_KEY=sk-...
   export ANTHROPIC_API_KEY=sk-ant-...
   export GOOGLE_API_KEY=AIza...
   export DEEPSEEK_API_KEY=sk-...
   ```
   > Only set the keys for providers you plan to use

3. **Run Hello World**
   ```bash
   python scripts/test_agent_flow.py
   ```
   Expected output:
   ```text
   Agent success:  True
   Agent output :  {'word_count': 7, 'text': 'Hello world from our new agent framework!'}
   ```

4. **Try Full System Demo**
   ```bash
   python scripts/test_complex_system.py
   ```
   This demonstrates:
   - 7-node workflow (4 LLM, 3 tools)
   - Level-based script chain
   - Router agent decision making
   - Multi-agent orchestration

## 🔧 Common Tasks

| Task | Command | Notes |
|------|---------|-------|
| Run a Chain | `python -m app.chains.orchestration.level_based_script_chain` | Execute a workflow chain |
| Start API Server | `uvicorn app.api.webhooks:app --reload` | Local development server |
| Run Tests | `pytest -q` | Quick test execution |
| Health Check | `make doctor` | System diagnostics |
| Update Docs | `make refresh-docs` | Regenerate documentation |
| Start REPL | `python -m ice_sdk.repl` | Interactive SDK shell |
| Deploy API | `docker compose up api` | Production deployment |

## 🛠️ Development

### Adding New Components

1. **Create a Tool**
   ```bash
   cursor ask "generate tool" --see src/app/tools/
   ```

2. **Add a Node**
   ```bash
   touch src/app/nodes/my_node.py && make refresh-docs
   ```

3. **Load Data**
   ```bash
   python -m app.tools.load_csv_vector --file data/my.csv
   ```

### Next Steps

1. Explore the codebase:
   - `src/app/agents/` - Agent implementations
   - `src/app/chains/` - Workflow chains
   - `src/app/tools/builtins/` - Tool implementations

2. Check the Architecture docs for design details

3. Build your own components:
   - Create tools under `app/tools/builtins/`
   - Add nodes in `app/nodes/`
   - Implement agents in `app/agents/`

## 📚 Documentation

Need more examples? Ask Cursor:
```
Generate docs/TOOLS_SQL_QUERY.md summarising src/app/tools/sql_query_tool.py
```

For detailed documentation:
- Architecture: See `docs/codebase_overview.md`
- API Reference: Check `docs/api/`
- Examples: Browse `examples/` 