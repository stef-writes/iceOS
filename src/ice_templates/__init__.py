"""Curated prompt templates shipped with IceOS.

Importing this package registers common templates into
`global_prompt_template_registry` so they are available at runtime without
extra code.  Downstream blueprints can reference them via
``prompt="template:csv.summary"``.
"""

from ice_core.models.llm import MessageTemplate
from ice_core.registry.prompt_template import register_prompt_template

__all__: list[str] = []


@register_prompt_template("csv.summary")
def _csv_summary() -> MessageTemplate:  # noqa: D401 – factory
    return MessageTemplate(
        role="system",
        content="""You are a helpful assistant. Summarise the following CSV rows\n\n{clean_rows_json}\n\nProvide a concise summary suitable for an operations dashboard.""",
        min_model_version="gpt-4",
        provider="openai",
    ) 