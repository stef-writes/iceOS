# ice_tools – Built-in Tools & Toolkits

This package ships **reference implementations** that are used by the example
workflows and the test-suite.  Importing `ice_tools` triggers an automatic
recursive import so every tool registers its factory function with
the global registry for fresh instances on each execution.

```python
import ice_tools          # one-liner – all tools now discoverable
```

---

## Directory layout

```
src/ice_tools/
    ├── __init__.py               # recursive importer
    ├── toolkits/
    │   ├── common/               # generic helpers (csv_loader, loop_tool, …)
    │   └── ecommerce/            # end-to-end listing workflow tools
    │       └── toolkit.py        # EcommerceToolkit factory
    └── README.md                 # you are here
```

### Common toolkit

| Tool name | Purpose |
|-----------|---------|
| `csv_loader`   | Read CSV → list[dict] (stdlib `csv` only) |
| `loop_tool`    | Iterate over items and call inner tool (second-class looping) |
| `mock_http_bin`| In-process FastAPI that stores POST bodies for inspection |
| `api_poster`   | Generic HTTP POST wrapper (uses httpx) |

### E-commerce toolkit

| Tool name | Purpose |
|-----------|---------|
| `pricing_strategy`         | cost → price with margin & rounding |
| `title_description_generator` | LLM-generated copy (test or live mode) |
| `marketplace_client`       | POST listing to external API (or simulate) |
| `listing_agent`            | Composite: price → copy → upload |
| `aggregator`               | Summarise per-item results |

---

## Registering a toolkit

```python
from ice_tools.toolkits.ecommerce import EcommerceToolkit

# All tools test-mode, no external I/O
EcommerceToolkit(test_mode=True, upload=False).register()
```

`register()` registers factory functions for each ToolBase subclass with shared config.
Fresh instances are created on each execution. Override settings (model, margin, upload) per
workflow as required.

---

## Creating your own toolkit

1. Subclass `ice_core.toolkits.base.BaseToolkit`.
2. Return fresh ToolBase instances in `get_tools()`.
3. Publish to PyPI; users enable it via `pip install your-toolkit && import your_toolkit`.

See `toolkits/ecommerce/toolkit.py` for a minimal, fully-typed example.
