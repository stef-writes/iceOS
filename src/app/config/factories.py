"""
Text Generation Node Configuration Factory

Provides pre-configured node setups for different use cases with:
- Version-controlled templates
- Model compatibility checks
- Input/output validation
- Production-ready defaults
"""

from dataclasses import dataclass
from typing import Any, Dict

# Import the default LevelBasedScriptChain implementation under a generic
# alias so that the factory can expose a stable *ScriptChain* name.
from app.chains.orchestration.level_based_script_chain import (
    LevelBasedScriptChain as ScriptChain,
)
from app.models.config import LLMConfig, MessageTemplate

# Corrected import paths -----------------------------------------------------
from app.models.node_models import NodeConfig, NodeMetadata

# Callback implementations ----------------------------------------------------
from app.utils.callbacks import LoggingCallback, MetricsCallback
from app.utils.context import ContextManager


@dataclass
class TextGenPreset:
    """Configuration preset for text generation nodes"""

    metadata: NodeMetadata
    llm_config: LLMConfig
    templates: Dict[str, MessageTemplate]  # Keyed by template role
    input_schema: Dict[str, str]
    output_schema: Dict[str, str]
    timeout: float = 30.0
    max_retries: int = 3


class TextGenerationConfigFactory:
    """Factory for creating pre-configured text generation nodes"""

    @staticmethod
    def create_from_preset(
        preset: TextGenPreset, context_manager: ContextManager
    ) -> Dict[str, Any]:
        """Create full node configuration from preset"""
        return {
            "config": NodeConfig(
                metadata=preset.metadata,
                llm_config=preset.llm_config,
                input_schema=preset.input_schema,
                output_schema=preset.output_schema,
                templates=list(preset.templates.values()),
                timeout=preset.timeout,
            ),
            "llm_config": preset.llm_config,
            "context_manager": context_manager,
        }

    # Predefined configurations
    @staticmethod
    def get_basic_generation_preset() -> TextGenPreset:
        """Basic text generation with GPT-3.5"""
        return TextGenPreset(
            metadata=NodeMetadata(
                node_id="text_gen_basic", node_type="text_generation", version="1.0.0"
            ),
            llm_config=LLMConfig(
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=500,
                max_context_tokens=2000,
            ),
            templates={
                "system": MessageTemplate(
                    role="system",
                    template="You are a helpful assistant. Context: {context}",
                    version="1.0.0",
                    min_model_version="gpt-3.5-turbo",
                ),
                "user": MessageTemplate(
                    role="user",
                    template="Task: {query}",
                    version="1.0.0",
                    min_model_version="gpt-3.5-turbo",
                ),
            },
            input_schema={"query": "str", "context": "str"},
            output_schema={"response": "str"},
        )

    @staticmethod
    def get_advanced_generation_preset() -> TextGenPreset:
        """Advanced generation with GPT-4 and structured output"""
        return TextGenPreset(
            metadata=NodeMetadata(
                node_id="text_gen_advanced",
                node_type="text_generation",
                version="2.0.0",
            ),
            llm_config=LLMConfig(
                model="gpt-4",
                temperature=0.5,
                max_tokens=1000,
                max_context_tokens=4000,
                top_p=0.9,
            ),
            templates={
                "system": MessageTemplate(
                    role="system",
                    template=(
                        "You are an expert AI assistant. Respond in JSON format.\n"
                        "Context: {context}\n"
                        "Rules: {rules}"
                    ),
                    version="2.0.0",
                    min_model_version="gpt-4",
                ),
                "user": MessageTemplate(
                    role="user",
                    template=(
                        "Task: {task}\n"
                        "Requirements:\n"
                        "- Format: {format_requirements}\n"
                        "- Style: {style}"
                    ),
                    version="2.0.0",
                    min_model_version="gpt-4",
                ),
            },
            input_schema={
                "task": "str",
                "context": "str",
                "rules": "str",
                "format_requirements": "str",
                "style": "str",
            },
            output_schema={
                "content": "str",
                "format": "str",
                "confidence_score": "float",
            },
            timeout=45.0,
            max_retries=5,
        )

    @staticmethod
    def get_code_generation_preset() -> TextGenPreset:
        """Specialized configuration for code generation"""
        return TextGenPreset(
            metadata=NodeMetadata(
                node_id="code_generator", node_type="code_generation", version="1.1.0"
            ),
            llm_config=LLMConfig(
                model="gpt-4",
                temperature=0.2,
                max_tokens=1500,
                max_context_tokens=4000,
                frequency_penalty=0.1,
            ),
            templates={
                "system": MessageTemplate(
                    role="system",
                    template=(
                        "You are an expert programmer specializing in {language}.\n"
                        "Follow these guidelines:\n"
                        "- Code style: {style_guide}\n"
                        "- Security: {security_rules}\n"
                        "- Performance: {performance_goals}"
                    ),
                    version="1.1.0",
                    min_model_version="gpt-4",
                ),
                "user": MessageTemplate(
                    role="user",
                    template=(
                        "Implement: {task}\n"
                        "Requirements:\n"
                        "{requirements}\n"
                        "Constraints:\n"
                        "{constraints}"
                    ),
                    version="1.1.0",
                    min_model_version="gpt-4",
                ),
            },
            input_schema={
                "language": "str",
                "task": "str",
                "style_guide": "str",
                "security_rules": "str",
                "performance_goals": "str",
                "requirements": "str",
                "constraints": "str",
            },
            output_schema={
                "code": "str",
                "documentation": "str",
                "tests": "str",
                "complexity_analysis": "str",
            },
            timeout=90.0,
        )


def create_script_chain(
    max_context_tokens: int = 4000, concurrency_level: int = 10
) -> ScriptChain:
    """Create a new ScriptChain instance with default configuration.

    Args:
        max_context_tokens: Maximum tokens for context window
        concurrency_level: Maximum concurrent node executions

    Returns:
        Configured ScriptChain instance
    """
    # Create callbacks
    callbacks = [LoggingCallback(), MetricsCallback()]

    # Create chain
    chain = ScriptChain(
        max_context_tokens=max_context_tokens,
        callbacks=callbacks,
        concurrency_level=concurrency_level,
    )

    return chain
