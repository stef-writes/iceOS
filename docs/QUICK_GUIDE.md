### Quick guide

- LLMOperatorConfig → LLMNodeConfig (code and schemas)
- CLI scaffold: `ice new llm-operator` → `ice new llm-node-tool`

Common tasks:

```bash
# Install deps
poetry install --with dev --no-interaction

# Health checks
make lint && make type && make test

# Format
make format

# Lint in CI mode
make format-check && make ci
```

Update imports and schema references:

```bash
grep -R "LLMOperatorConfig" -n src tests docs | xargs sed -i '' 's/LLMOperatorConfig/LLMNodeConfig/g'
```

Regenerate schemas:

```bash
poetry run ice export-schemas --format json
```

### Plugins (starter packs)

Load optional tools/agents/LLM helpers via declarative plugin manifests.

1) Create a plugins.v0 manifest (YAML or JSON):

```yaml
components:
  - node_type: tool
    name: writer_tool
    import_path: ice_tools.generated.writer_tool:create_writer_tool
  - node_type: agent
    name: demo_agent
    import_path: acme.agents.demo:create_demo_agent
  - node_type: llm
    name: echo_llm
    import_path: acme.llms.echo:create_echo_llm
```

2) Point the API to your manifests:

```bash
export ICEOS_PLUGIN_MANIFESTS=/path/to/plugins.yml,/path/to/extra.json
docker compose up api
```

Validate manifests without dynamic imports:

```bash
ice plugins lint /path/to/plugins.yml
```
