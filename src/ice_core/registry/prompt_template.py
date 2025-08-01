"""Prompt template registry for managing reusable message templates."""

from typing import Dict, Optional, Callable
from ice_core.models.llm import MessageTemplate
from ice_core.models.enums import ModelProvider


class PromptTemplateRegistry:
    """Registry for managing prompt templates.
    
    Enables dynamic prompt selection and management, allowing
    different prompts to be used based on context, model capabilities,
    or other runtime conditions.
    """
    
    def __init__(self) -> None:
        """Initialize an empty prompt template registry."""
        self._templates: Dict[str, MessageTemplate] = {}
    
    def register(self, name: str, template: MessageTemplate) -> None:
        """Register a prompt template.
        
        Args:
            name: Unique name for the template
            template: The MessageTemplate to register
            
        Raises:
            ValueError: If a template with this name already exists
        """
        if name in self._templates:
            raise ValueError(f"Template '{name}' already registered")
        self._templates[name] = template
    
    def get(self, name: str) -> MessageTemplate:
        """Get a registered template by name.
        
        Args:
            name: Name of the template to retrieve
            
        Returns:
            The registered MessageTemplate
            
        Raises:
            KeyError: If template not found
        """
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found")
        return self._templates[name]
    
    def get_optional(self, name: str) -> Optional[MessageTemplate]:
        """Get a template if it exists, otherwise return None.
        
        Args:
            name: Name of the template to retrieve
            
        Returns:
            The template if found, None otherwise
        """
        return self._templates.get(name)
    
    def list_templates(self) -> list[str]:
        """List all registered template names.
        
        Returns:
            List of registered template names
        """
        return list(self._templates.keys())
    
    def has_template(self, name: str) -> bool:
        """Check if a template is registered.
        
        Args:
            name: Name to check
            
        Returns:
            True if template exists
        """
        return name in self._templates
    
    def unregister(self, name: str) -> Optional[MessageTemplate]:
        """Remove a template from the registry.
        
        Args:
            name: Name of template to remove
            
        Returns:
            The removed template if it existed
        """
        return self._templates.pop(name, None)
    
    def clear(self) -> None:
        """Clear all registered templates."""
        self._templates.clear()
    
    def __len__(self) -> int:
        """Return the number of registered templates."""
        return len(self._templates)
    
    def __contains__(self, name: str) -> bool:
        """Check if a template name is registered."""
        return name in self._templates
    
    def get_by_criteria(
        self,
        provider: Optional[str] = None,
        min_version: Optional[str] = None,
        role: Optional[str] = None
    ) -> Dict[str, MessageTemplate]:
        """Get templates matching specific criteria.
        
        Args:
            provider: Filter by model provider
            min_version: Filter by minimum model version
            role: Filter by message role
            
        Returns:
            Dict of matching templates
        """
        results = {}
        for name, template in self._templates.items():
            if provider and template.provider != provider:
                continue
            if min_version and template.min_model_version != min_version:
                continue
            if role and template.role != role:
                continue
            results[name] = template
        return results


# Global singleton instance
global_prompt_template_registry = PromptTemplateRegistry()


def register_prompt_template(name: str) -> Callable[[Callable[[], MessageTemplate]], Callable[[], MessageTemplate]]:
    """Decorator to register a prompt template.
    
    Usage:
        @register_prompt_template("my_prompt")
        def create_prompt() -> MessageTemplate:
            return MessageTemplate(...)
    
    Args:
        name: Name to register the template under
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable[[], MessageTemplate]) -> Callable[[], MessageTemplate]:
        # Create and register the template
        template = func()
        global_prompt_template_registry.register(name, template)
        return func
    return decorator


# Pre-registered common templates
def _register_default_templates() -> None:
    """Register default system templates."""
    # Basic templates that can be overridden
    try:
        global_prompt_template_registry.register(
            "default_system",
            MessageTemplate(
                role="system",
                content="You are a helpful AI assistant.",
                version="1.0.0",
                min_model_version="gpt-4",
                provider=ModelProvider.OPENAI
            )
        )
        
        global_prompt_template_registry.register(
            "chain_of_thought",
            MessageTemplate(
                role="user",
                content="Let's think step by step about this: {query}",
                version="1.0.0",
                min_model_version="gpt-4",
                provider=ModelProvider.OPENAI
            )
        )
        
        global_prompt_template_registry.register(
            "json_response",
            MessageTemplate(
                role="system",
                content="Always respond with valid JSON. {format_instructions}",
                version="1.0.0",
                min_model_version="gpt-4",
                provider=ModelProvider.OPENAI
            )
        )
    except ValueError:
        # Templates already registered, ignore
        pass


# Register defaults on module import
_register_default_templates() 