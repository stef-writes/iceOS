# iceOS Quick Guide ⭐️

Copy-paste these snippets in your terminal or IDE to get productive fast.

| # | Goal | Snippet |
|---|------|---------|
| 1 | Run a Chain | `python -m app.chains.orchestration.level_based_script_chain` |
| 2 | Add a Tool | `cursor ask "generate tool" --see src/app/tools/` |
| 3 | Trigger webhook locally | `uvicorn app.api.webhooks:app --reload` |
| 4 | Index CSV into vector DB | `python -m app.tools.load_csv_vector --file data/my.csv` |
| 5 | Register new Node | `touch src/app/nodes/my_node.py && make refresh-docs` |
| 6 | Doctor health check | `make doctor` |
| 7 | Regenerate docs | `make refresh-docs` |
| 8 | Run all tests | `pytest -q` |
| 9 | Start REPL with SDK loaded | `python -m ice_sdk.repl` |
|10 | Deploy reference API | `docker compose up api` |

---

Need more examples? Ask Cursor:

```
Generate docs/TOOLS_SQL_QUERY.md summarising src/app/tools/sql_query_tool.py
``` 