### Breaking changes (CLI and node naming)

- LLMOperatorConfig → LLMNodeConfig (code and schemas)
- CLI scaffold: `ice new llm-operator` → `ice new llm-node-tool`

Update imports and schema references:

```bash
grep -R "LLMOperatorConfig" -n src tests docs | xargs sed -i '' 's/LLMOperatorConfig/LLMNodeConfig/g'
```

Regenerate schemas:

```bash
poetry run ice export-schemas --format json
```
