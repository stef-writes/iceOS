"""Registry package for ice_core.

Contains registries for various core components like prompt templates.
"""

from ice_core.exceptions import RegistryError
from .prompt_template import (
    PromptTemplateRegistry,
    global_prompt_template_registry,
    register_prompt_template,
)

__all__ = [
    "RegistryError",
    "PromptTemplateRegistry",
    "global_prompt_template_registry", 
    "register_prompt_template",
] 