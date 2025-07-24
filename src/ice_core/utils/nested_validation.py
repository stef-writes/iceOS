"""Nested output validation utilities (moved from validation.py)."""

from __future__ import annotations

from typing import Any, Dict, List

try:
    import dpath as _dpath_util  # type: ignore

    def _get_nested(obj: Any, path: str, *, separator: str = ".") -> Any:
        return _dpath_util.get(obj, path, separator=separator)

except ModuleNotFoundError:

    def _get_nested(obj: Any, path: str, *, separator: str = ".") -> Any:  # type: ignore[return-value]
        if "*" in path:
            raise ImportError(
                "dpath required for wildcard path validation. Install via 'pip install dpath'."
            )
        current = obj
        for segment in path.split(separator):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                raise KeyError(path)
        return current

__all__ = ["validate_nested_output"]

def validate_nested_output(output: Any, schema: Dict[str, type]) -> List[str]:
    errors: List[str] = []
    for key_path, expected_type in schema.items():
        try:
            value = _get_nested(output, key_path, separator=".")
            if not isinstance(value, expected_type):
                errors.append(
                    f"Path '{key_path}': Expected {expected_type.__name__}, got {type(value).__name__}"
                )
        except KeyError:
            errors.append(f"Path '{key_path}': Missing in output")
    return errors
