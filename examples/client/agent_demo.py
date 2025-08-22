from __future__ import annotations

import asyncio

from ice_client import IceClient


async def main() -> None:
    client = IceClient()

    # Compose a simple data-first agent definition
    await client.compose_agent(
        name="demo_agent",
        system_prompt="You are concise.",
        tools=["writer_tool"],
        llm_config={"provider": "openai", "model": "gpt-4o"},
    )

    # One chat turn
    resp = await client.chat_turn("demo_agent", session_id="s1", user_message="Hello")
    print(resp)


if __name__ == "__main__":
    asyncio.run(main())
