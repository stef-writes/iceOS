# app.tools – built-in Tools

| Tool | Description |
| ---- | ----------- |
| `WordCountTool` (`word_count`) | Count the words in a given text; returns count + original text. |

To implement your own Tool:
1. Subclass `ice_sdk.BaseTool`.
2. Define `name`, `description`, `parameters_schema`, and `output_schema`.
3. Implement async `run()` with side-effects isolated inside.

After adding a new Tool, run `make refresh-docs` so it appears in `CAPABILITY_CATALOG.json`. 