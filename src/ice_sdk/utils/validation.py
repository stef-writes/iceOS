"""Nested output validation utilities.
# ruff: noqa: E402

This helper complements ``ice_sdk.core.validation`` by supporting *nested* key
paths (dot-separated) when validating dictionaries returned by ScriptChain
nodes.

The implementation relies on `dpath` for flexible traversal while staying
fully type-hinted.
"""

from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Optional dependency: dpath ------------------------------------------------
# ---------------------------------------------------------------------------
try:
    import dpath.util as _dpath_util  # type: ignore

    def _get_nested(obj: Any, path: str, *, separator: str = ".") -> Any:
        """Proxy to *dpath.util.get* when the library is available."""

        return _dpath_util.get(obj, path, separator=separator)

except ModuleNotFoundError:  # pragma: no cover – soft fallback

    def _get_nested(obj: Any, path: str, *, separator: str = ".") -> Any:  # type: ignore[return-value]
        """Lightweight fallback that supports **exact** key paths only.

        Wildcards and advanced selectors are **not** supported without the
        optional *dpath* dependency.  The behaviour is good enough for basic
        tests but raises a clear :class:`ImportError` when an unsupported
        path expression is encountered.
        """

        if "*" in path:
            raise ImportError(
                "dpath is required for wildcard path validation but is not\n"
                "installed.  Run `pip install dpath` or install iceOS with\n"
                "the extra dependencies via `pip install 'iceos[dpath]'`."
            )

        current = obj
        for segment in path.split(separator):
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                raise KeyError(path)
        return current


__all__ = ["validate_nested_output"]


def validate_nested_output(
    output: Any, schema: Dict[str, type]
) -> List[str]:  # noqa: D401
    """Validate *output* against *schema* and return a list of error strings.

    Parameters
    ----------
    output
        Arbitrary Python object (usually a ``dict``) produced by a node.
    schema
        Mapping of *dot-separated key paths* → *expected Python type*.

    Notes
    -----
    • A "*" wildcard matches any single level (e.g. ``results.*.score``).
    • An empty error list means validation succeeded.
    """

    errors: List[str] = []

    for key_path, expected_type in schema.items():
        try:
            value = _get_nested(output, key_path, separator=".")
            if not isinstance(value, expected_type):
                errors.append(
                    f"Path '{key_path}': Expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )
        except KeyError:
            errors.append(f"Path '{key_path}': Missing in output")
    return errors
