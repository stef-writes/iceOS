from __future__ import annotations

import asyncio
from typing import Any, Dict

from ice_client import IceClient


async def main() -> None:
    client = IceClient()
    # Minimal LLM node blueprint
    bp: Dict[str, Any] = {
        "schema_version": "1.2.0",
        "nodes": [
            {
                "id": "llm1",
                "type": "llm",
                "model": "gpt-4o",
                "prompt": "Say hello to {{ inputs.name }}",
                "llm_config": {"provider": "openai", "model": "gpt-4o"},
            }
        ],
    }
    exec_id = await client.run(blueprint=bp, inputs={"name": "World"})
    result = await client.poll_until_complete(exec_id, timeout=30)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
