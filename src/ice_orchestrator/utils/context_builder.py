from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from ice_core.exceptions import ErrorCode
from ice_orchestrator.errors import ChainError

if TYPE_CHECKING:  # pragma: no cover
    from ice_core.models import NodeConfig, NodeExecutionResult


class ContextBuilder:  # – utility helper
    """Helper responsible for constructing per-node execution contexts.

    Extracted verbatim from `ScriptChain._build_node_context` so unit-tests and
    behavioural semantics remain unchanged.
    """

    # ------------------------------------------------------------------
    # Public helpers ----------------------------------------------------
    # ------------------------------------------------------------------

    @staticmethod
    def build_node_context(
        node: "NodeConfig",
        accumulated_results: Dict[str, "NodeExecutionResult"],
    ) -> Dict[str, Any]:
        """Re-create the *input* context for *node* based on its declared
        `input_mappings` and the outputs of dependency nodes.
        """

        context: Dict[str, Any] = {}
        validation_errors: List[str] = []

        if getattr(node, "input_mappings", None):
            for placeholder, mapping in node.input_mappings.items():  # type: ignore[attr-defined]
                if (
                    isinstance(mapping, dict) and "source_node_id" in mapping
                ) or hasattr(mapping, "source_node_id"):
                    dep_id = (
                        mapping["source_node_id"]
                        if isinstance(mapping, dict)
                        else mapping.source_node_id  # type: ignore[index]
                    )
                    output_key = (
                        mapping["source_output_key"]
                        if isinstance(mapping, dict)
                        else mapping.source_output_key  # type: ignore[index]
                    )
                    dep_result = accumulated_results.get(dep_id)

                    if not dep_result or not dep_result.success:
                        validation_errors.append(
                            f"Dependency '{dep_id}' failed or did not run."
                        )
                        continue

                    try:
                        value = ContextBuilder.resolve_nested_path(
                            dep_result.output, output_key
                        )
                        context[placeholder] = value
                    except (KeyError, IndexError, TypeError) as exc:
                        validation_errors.append(
                            f"Failed to resolve path '{output_key}' in dependency '{dep_id}': {exc}"
                        )
                else:
                    context[placeholder] = mapping  # literal / raw value

        if validation_errors:
            raise ChainError(
                ErrorCode.UNKNOWN,
                f"Node '{node.id}' context validation failed:\n"  # type: ignore[attr-defined]
                + "\n".join(validation_errors),
            )

        return context

    # ------------------------------------------------------------------
    # Static helpers ----------------------------------------------------
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_nested_path(data: Any, path: str) -> Any:  # – generic
        """Resolve *path* in *data* using dot-notation.

        Special cases
        -------------
        * ``path in ("", ".")`` → return *data* unchanged.
        """
        if not path or path == ".":
            return data

        for key in path.split("."):
            if isinstance(data, dict):
                data = data[key]
            elif isinstance(data, list):
                data = data[int(key)]
            else:
                raise TypeError(f"Cannot resolve path '{path}' in {type(data)}")
        return data
