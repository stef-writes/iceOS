"""Shared helper utilities for builtin node executors."""

from __future__ import annotations

from typing import Any, Dict, Set

__all__: list[str] = [
    "flatten_dependency_outputs",
    "resolve_jinja_templates",
]


def flatten_dependency_outputs(
    merged_inputs: Dict[str, Any], tool: Any
) -> Dict[str, Any]:
    """Smart parameter flattening so workflow context can be passed directly."""
    try:
        import inspect

        execute_method = getattr(tool, "_execute_impl", None)
        if not execute_method:
            return merged_inputs  # fallback

        sig = inspect.signature(execute_method)
        expected_params: Set[str] = set(sig.parameters.keys()) - {"self", "kwargs"}

        flattened = merged_inputs.copy()
        for key, value in merged_inputs.items():
            if isinstance(value, dict) and key not in expected_params:
                for param in expected_params:
                    if param in value and param not in flattened:
                        flattened[param] = value[param]
        return flattened
    except Exception:
        return merged_inputs


def resolve_jinja_templates(
    data: Any, context: Dict[str, Any]
) -> Any:  # noqa: ANN401 – dynamic
    """Recursively resolve {{var}} templates in *data* using *context*."""
    try:
        import jinja2

        # Fail fast on unresolved variables in templates
        env = jinja2.Environment(autoescape=False, undefined=jinja2.StrictUndefined)

        def _resolve(value: Any) -> Any:  # noqa: ANN401
            if isinstance(value, str) and "{{" in value and "}}" in value:
                template = env.from_string(value)
                # Render against the cleaned base context that unwraps
                # NodeExecutionResult-like dicts into their 'output'.
                return template.render(**base_ctx)
            if isinstance(value, dict):
                return {k: _resolve(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_resolve(v) for v in value]
            return value

        # Ensure dependency outputs are addressable by id in context
        # If a context key maps to a NodeExecutionResult-like dict, unwrap
        base_ctx = {}
        for k, v in context.items():
            try:
                if (
                    isinstance(v, dict)
                    and "success" in v
                    and ("output" in v or "error" in v)
                ):
                    base_ctx[k] = v.get("output", v)
                else:
                    base_ctx[k] = v
            except Exception:
                base_ctx[k] = v

        return _resolve(data)
    except ModuleNotFoundError:
        return data
