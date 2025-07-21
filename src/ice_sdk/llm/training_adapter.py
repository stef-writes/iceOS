import json
from pathlib import Path

from pydantic import BaseModel

from ice_sdk.models import ChainSpec


class TrainingExample(BaseModel):
    prompt: str
    chain: ChainSpec
    source_file: str  # Track origin for updates


def generate_from_examples():
    examples_dir = Path("examples/scenarios")
    output_file = Path("examples/training_data/dataset.jsonl")

    with output_file.open("w") as f:
        for example_path in examples_dir.glob("*.py"):
            # Extract prompt from example docstring
            with open(example_path) as py_file:
                docstring = py_file.read().split('"""')[1]
                prompt = docstring.split("\n")[0].strip()

            # Convert example to ChainSpec (from your existing loader patterns)
            # TODO: Implement load_example_chain function
            # chain = load_example_chain(example_path)  # Reuse your existing chain loader
            chain = ChainSpec()  # Placeholder for now

            # Create training entry
            entry = TrainingExample(
                prompt=prompt, chain=chain, source_file=str(example_path)
            )

            f.write(entry.model_dump_json() + "\n")


if __name__ == "__main__":
    generate_from_examples()


def convert_to_chat_format(example: TrainingExample) -> dict:
    """Convert to OpenAI fine-tuning format"""
    return {
        "messages": [
            {"role": "user", "content": example.prompt},
            {"role": "assistant", "content": json.dumps(example.chain.model_dump())},
        ]
    }
