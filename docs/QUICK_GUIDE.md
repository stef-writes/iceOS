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
