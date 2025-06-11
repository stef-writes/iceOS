"""
Script to run the character story generation chain from template
"""

import asyncio
import json
from pathlib import Path

import httpx


async def run_character_story():
    # Load the template
    template_path = (
        Path(__file__).parent.parent / "templates" / "character_story_chain.json"
    )
    with open(template_path) as f:
        chain_config = json.load(f)

    # Execute the chain with increased timeout
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/chains/execute", json=chain_config
            )

            if response.status_code == 200:
                result = response.json()
                if result["success"]:
                    print("\nCharacter Story Chain Results:")
                    print("=" * 80)

                    # Print Characters
                    print("\nGenerated Characters:")
                    print("-" * 40)
                    characters_raw = result["output"]["character_generator"]["output"][
                        "characters"
                    ]
                    # Handle both string and dict cases
                    if isinstance(characters_raw, str):
                        try:
                            characters_raw = json.loads(characters_raw)
                        except Exception as e:
                            print("Error parsing characters_raw as JSON:", e)
                            print("Raw value:", characters_raw)
                            characters_raw = {"characters": []}
                    characters = characters_raw.get("characters", [])
                    for char in characters:
                        print(f"\nName: {char['name']}")
                        print(f"Personality: {char['personality']}")
                        print(f"Background: {char['background']}")

                    # Print Story
                    print("\nGenerated Story:")
                    print("-" * 40)
                    print(result["output"]["story_generator"]["output"]["story"])

                    # Print Character Analysis
                    print("\nCharacter Relationships:")
                    print("-" * 40)
                    relationships_raw = result["output"]["character_analysis"][
                        "output"
                    ]["relationships"]
                    if isinstance(relationships_raw, str):
                        try:
                            relationships_raw = json.loads(relationships_raw)
                        except Exception as e:
                            print("Error parsing relationships_raw as JSON:", e)
                            print("Raw value:", relationships_raw)
                            relationships_raw = {"relationships": []}

                    relationships = relationships_raw.get("relationships", [])
                    for rel in relationships:
                        print(f"\n{rel['character']}:")
                        for interaction in rel["interactions"]:
                            print(f"  • With {interaction['character']}:")
                            print(f"    {interaction['description']}")

                    # Print Summary
                    print("\nStory Summary:")
                    print("-" * 40)
                    print(result["output"]["story_summarizer"]["output"]["summary"])

                    # Print Stats
                    print("\nExecution Stats:")
                    print("-" * 40)
                    print(f"Total tokens: {result['token_stats']['total_tokens']}")
                    print(f"Execution time: {result['execution_time']:.2f} seconds")
                else:
                    print("Error:", result["error"])
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
        except httpx.TimeoutException:
            print(
                "Error: Request timed out. The chain might be taking too long to execute."
            )
        except httpx.RequestError as e:
            print(f"Error: Failed to make request: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_character_story())
