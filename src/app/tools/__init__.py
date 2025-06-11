"""Side-effecting Tools used by iceOS.

This package aggregates *built-in* tools in `app.tools.builtins` and acts as
public façade so that import paths stay stable even if we later move files.

Example:

```python
from app.tools import WordCountTool
```

| Export | Purpose |
| ------ | ------- |
| `WordCountTool` | Count words in a text. |
"""

from app.tools.builtins.word_count import WordCountTool  # noqa: F401

__all__ = [
    "WordCountTool",
]
