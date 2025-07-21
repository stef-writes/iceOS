from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel


class TrainingExample(BaseModel):
    prompt: str
    chain: Dict[str, Any]
    source_file: str  # Track origin for updates


# ---------------------------------------------------------------------------
# Placeholder loader – replace with actual implementation once examples migrate
# ---------------------------------------------------------------------------


def load_example_chain(path: Path) -> Dict[str, Any]:  # noqa: D401 – stub
    """Return minimal chain payload so the script remains functional.

    The previous implementation relied on deprecated loaders.  Until the
    example suite is refactored we output an *empty* dict so downstream code
    can still iterate over generated dataset lines.
    """

    return {}


def generate_from_examples():
    base_dir = Path(__file__).parent.parent
    examples_dir = base_dir / "examples" / "scenarios"
    output_file = base_dir / "examples" / "training_data" / "dataset.jsonl"

    with output_file.open("w") as f:
        for example_path in examples_dir.glob("*.py"):
            # Extract prompt from example docstring
            with open(example_path) as py_file:
                docstring = py_file.read().split('"""')[1]
                prompt = docstring.split("\n")[0].strip()

            # Convert example to ChainSpec (from your existing loader patterns)
            chain = load_example_chain(example_path)  # Reuse your existing chain loader

            # Create training entry
            entry = TrainingExample(
                prompt=prompt, chain=chain, source_file=str(example_path)
            )

            f.write(entry.model_dump_json() + "\n")


if __name__ == "__main__":
    generate_from_examples()
