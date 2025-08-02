"""Stub o3 provider for Frosty."""
from __future__ import annotations

import json
import re
from typing import Any

from .base import LLMProvider

class O3Provider:
    name = "o3"

    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        m = re.search(r"say hello to (.+)", prompt, re.I)
        if m:
            name = m.group(1).strip()
            return json.dumps({
                "nodes": [{
                    "id": "greet",
                    "type": "tool",
                    "tool_name": "hello",
                    "tool_args": {"name": name}
                }]
            })
        return "{}"

PROVIDER: LLMProvider = O3Provider()