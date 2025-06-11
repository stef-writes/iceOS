import json
import pathlib

from app.models.config import AppConfig, LLMConfig, MessageTemplate
from app.models.node_models import (  # type: ignore
    AiNodeConfig,
    NodeConfig,
    ToolConfig,
    ToolNodeConfig,
)

SCHEMA_DIR = pathlib.Path(__file__).resolve().parent.parent / "schemas"
SCHEMA_DIR.mkdir(exist_ok=True)

MODELS = {
    "LLMConfig": LLMConfig,
    "MessageTemplate": MessageTemplate,
    "AppConfig": AppConfig,
    "NodeConfig": NodeConfig,
    "AiNodeConfig": AiNodeConfig,
    "ToolNodeConfig": ToolNodeConfig,
    "ToolConfig": ToolConfig,
}

for name, model in MODELS.items():
    schema_path = SCHEMA_DIR / f"{name}.json"
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(model.model_json_schema(), f, indent=2)
    print(f"Wrote {schema_path.relative_to(pathlib.Path.cwd())}")
