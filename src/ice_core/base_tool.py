"""Base tool implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class ToolBase(BaseModel, ABC):
    """Base class for all tool implementations.
    
    Tools are stateless, idempotent operations that may have side effects.
    They expose their capabilities through schemas and a standard execute method.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    # Required attributes - must be set by subclasses
    name: str = ""
    description: str = ""
    
    @abstractmethod
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Override in subclasses to provide tool-specific logic."""
        pass
    
    async def execute(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute the tool with given inputs.
        
        Subclasses should override _execute_impl.
        """
        
        try:
            # Validate inputs
            self._validate_inputs(kwargs)
            
            # Execute implementation
            result = await self._execute_impl(**kwargs)
            
            # Validate outputs
            self._validate_outputs(result)
            
            return result
            
        except Exception:
            # Tools should handle their own errors appropriately
            raise
    
    def _validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate *inputs* against the merged input schema.

        Sub-classes normally do **not** override this – they should rely on the
        automatic schema derived from the class fields **plus** the
        `_execute_impl` signature.  If a tool needs custom validation it can
        still override the method but should call ``super()._validate_inputs``
        first so the JSON-Schema check remains in effect.
        """
        from ice_core.validation.input_validator import validate_tool_inputs  # local import to avoid cycles

        schema = self.get_input_schema()
        ok, errors, _ = validate_tool_inputs(schema, inputs)
        if not ok:
            from ice_core.exceptions import ValidationError as IceValidationError  # type: ignore

            raise IceValidationError(
                f"Input validation failed for tool '{self.name}': " + "; ".join(errors)
            )

    def _validate_outputs(self, outputs: Dict[str, Any]) -> None:
        """Validate outputs against declared output schema (if any)."""
        from ice_core.utils.json_schema import validate_with_schema  # local import

        schema = self.get_output_schema()
        if schema:
            ok, errors, _ = validate_with_schema(outputs, schema)
            if not ok:
                from ice_core.exceptions import ValidationError as IceValidationError  # type: ignore

                raise IceValidationError(
                    f"Output validation failed for tool '{self.name}': " + "; ".join(errors)
                )

    # ------------------------------------------------------------------
    # Schema generation helpers ----------------------------------------
    # ------------------------------------------------------------------

    @classmethod
    def _signature_properties_and_required(cls) -> tuple[Dict[str, Any], list[str]]:
        """Introspect `_execute_impl` and convert parameters to JSON-Schema props."""
        import inspect
        from typing import Any, get_origin, get_args, Union

        def annotation_to_schema(annotation: Any) -> Dict[str, Any]:
            """Map Python type annotations to minimal JSON-Schema fragments."""
            origin = get_origin(annotation)
            args = get_args(annotation)

            # Handle Optional[T] (Union[T, None])
            if origin is Union and len(args) == 2 and type(None) in args:  # type: ignore[name-defined]
                actual = args[0] if args[1] is type(None) else args[1]  # noqa: E721
                schema = annotation_to_schema(actual)
                # optional – handled by 'required' list in caller
                return schema

            mapping = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
                dict: "object",
                list: "array",
            }
            if annotation in mapping:
                return {"type": mapping[annotation]}
            # Fallback – open schema
            return {}

        sig = inspect.signature(cls._execute_impl)
        properties: Dict[str, Any] = {}
        required: list[str] = []

        for name, param in sig.parameters.items():
            if name in {"self", "cls"}:
                continue
            prop_schema = annotation_to_schema(param.annotation)
            properties[name] = prop_schema
            if param.default is inspect._empty:
                required.append(name)

        return properties, required

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return JSON Schema for tool inputs (Pydantic fields + method params)."""
        # 1. Schema from Pydantic model (may include additional custom fields)
        model_schema: Dict[str, Any] = cls.model_json_schema()
        model_props: Dict[str, Any] = model_schema.get("properties", {})
        model_required: list[str] = model_schema.get("required", [])

        # 2. Schema from _execute_impl signature
        sig_props, sig_required = cls._signature_properties_and_required()

        # 3. Merge – signature takes precedence for overlapping keys because it
        #    reflects runtime expectations.
        merged_properties = {**model_props, **sig_props}
        merged_required = sorted(set(model_required).union(sig_required))

        return {
            "type": "object",
            "properties": merged_properties,
            "required": merged_required,
            "additionalProperties": False,
        }

    @classmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        """Return JSON schema for tool outputs. Sub-classes should override."""
        return {
            "type": "object",
            "properties": {
                "result": {},  # open schema – override for concrete tools
            },
        } 