"""Common abstract base class for all node implementations.

This is an *identical* copy of the legacy ``ice_orchestrator.nodes.base.BaseNode`` but now
lives inside ``ice_sdk`` so that external packages can depend on a stable path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, cast

from pydantic import ValidationError, create_model

from ice_core.models import NodeMetadata
from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult


class BaseNode(ABC):
    """Abstract base class for all nodes.

    Provides:
    - Lifecycle hooks (pre_execute, post_execute)
    - Input validation using schema
    - Core node properties and configuration
    """

    def __init__(self, config: NodeConfig):
        self.config = config

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    @property
    def node_id(self) -> str:
        """Return the underlying node UUID (guaranteed post-validation)."""
        return cast(str, cast(NodeMetadata, self.config.metadata).node_id)  # type: ignore[attr-defined,redundant-cast]

    @property
    def node_type(self) -> str:
        return cast(str, cast(NodeMetadata, self.config.metadata).node_type)  # type: ignore[attr-defined,redundant-cast]

    @property
    def id(self) -> str:
        return cast(str, self.config.id)  # type: ignore[redundant-cast]

    @property
    def llm_config(self) -> Any:  # – provider specific
        return getattr(self, "_llm_config", getattr(self.config, "llm_config", None))

    @property
    def dependencies(self) -> list[str]:
        return cast(list[str], self.config.dependencies)  # type: ignore[redundant-cast]

    # ------------------------------------------------------------------
    # Lifecycle hooks ----------------------------------------------------
    # ------------------------------------------------------------------
    async def pre_execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and potentially transform *context* before :py:meth:`execute`."""
        if not await self.validate_input(context):
            raise ValueError("Input validation failed")
        return context

    async def post_execute(self, result: NodeExecutionResult) -> NodeExecutionResult:
        return result

    # ------------------------------------------------------------------
    # Validation helpers -------------------------------------------------
    # ------------------------------------------------------------------
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        # Allow dynamic schema adaptation based on context.
        if hasattr(self.config, "adapt_schema_from_context"):
            self.config.adapt_schema_from_context(context)  # type: ignore[attr-defined]

        schema = self.config.input_schema
        if not schema:
            return True

        if hasattr(
            self.config, "is_pydantic_schema"
        ) and self.config.is_pydantic_schema(schema):
            try:
                schema.model_validate(context)  # type: ignore[attr-defined,union-attr]
                return True
            except ValidationError:
                return False

        # Dict-based validation fallback.
        if isinstance(schema, dict):
            try:
                fields = {
                    key: (eval(type_str), ...) for key, type_str in schema.items()
                }  # – eval on trusted input
                InputModel = create_model("InputModel", **fields)  # type: ignore[call-arg,call-overload]
                InputModel(**context)  # type: ignore[call-arg]
                return True
            except (ValidationError, NameError, SyntaxError):
                return False

        # Unsupported schema type; consider validation failed.
        return False

    # ------------------------------------------------------------------
    # Schema accessors -------------------------------------------------
    # ------------------------------------------------------------------
    @property
    def input_schema(self) -> Any:  # – may be Pydantic model or Dict
        """Return the declared *input* schema for this node, if any.

        The base implementation simply forwards the attribute from the wrapped
        :class:`~ice_sdk.models.node_models.NodeConfig` instance.  Sub-classes
        can override to provide dynamic behaviour.
        """

        return getattr(self.config, "input_schema", None)

    @property
    def output_schema(self) -> Any:  # – may be Pydantic model or Dict
        """Return the declared *output* schema for this node, if any."""

        return getattr(self.config, "output_schema", None)

    # ------------------------------------------------------------------
    # Runtime validation -----------------------------------------------
    # ------------------------------------------------------------------

    def runtime_validate(self) -> None:  # – optional hook
        """Idempotent runtime validation delegated to the config object.

        This is a thin convenience wrapper that makes sure *every* node
        instance exposes a **runtime_validate()** method as required by
        orchestration logic.  If the underlying config class provides its
        own implementation we simply call through; otherwise we perform no
        additional checks (the node is considered valid).
        """

        if hasattr(self.config, "runtime_validate"):
            # Delegate to the Pydantic model's validation routine
            self.config.runtime_validate()
        # No else branch – absence of the method means no extra validation

    # ------------------------------------------------------------------
    # Abstract method ----------------------------------------------------
    # ------------------------------------------------------------------
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> NodeExecutionResult:
        """Execute node logic (to be provided by subclasses)."""
        raise NotImplementedError
