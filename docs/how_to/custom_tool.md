# How-to: Build a Custom Tool

1. Create `my_tool.tool.py` anywhere under your repo.
2. Subclass `BaseTool`, fill metadata and implement `run`.
3. Return JSON-serialisable data only.
4. Ensure any network / file IO is awaited.
5. Run `ice tool test my_tool -a '{"foo": "bar"}'`.

Detailed tutorial coming soon. 