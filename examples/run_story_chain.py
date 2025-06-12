"""
Script to run the story generation chain from template
"""

import asyncio
import json
from pathlib import Path

import httpx


async def run_story_chain():
    # Load the template
    template_path = Path(__file__).parent / "templates" / "story_chain.json"
    with open(template_path) as f:
        chain_config = json.load(f)

    # Execute the chain
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/chains/execute", json=chain_config
        )

        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print("\nStory Generation Chain Results:")
                print("-" * 50)
                print("\nGenerated Story:")
                print(result["output"]["story_generator"]["output"]["story"])
                print("\nSummary:")
                print(result["output"]["story_summarizer"]["output"])
                print("\nExecution Stats:")
                print(f"Total tokens: {result['token_stats']['total_tokens']}")
                print(f"Execution time: {result['execution_time']:.2f} seconds")
            else:
                print("Error:", result["error"])
        else:
            print(f"Error: {response.status_code}")
            print(response.text)


if __name__ == "__main__":
    asyncio.run(run_story_chain())
