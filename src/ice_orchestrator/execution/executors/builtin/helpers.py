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

        env = jinja2.Environment(autoescape=False)

        def _resolve(value: Any) -> Any:  # noqa: ANN401
            if isinstance(value, str) and "{{" in value and "}}" in value:
                template = env.from_string(value)
                return template.render(**context)
            if isinstance(value, dict):
                return {k: _resolve(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_resolve(v) for v in value]
            return value

        return _resolve(data)
    except ModuleNotFoundError:
        return data
