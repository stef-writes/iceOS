"""Validation helpers for ScriptChain execution.

This module centralises validation and control-flow logic that used to live
inside `script_chain.py`, improving separation of concerns and testability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Mapping, Set

from structlog import get_logger

from ice_sdk.context.type_manager import context_type_manager

if TYPE_CHECKING:  # pragma: no cover
    from ice_core.models.node_models import NodeConfig
    from ice_core.models.script_chain import ChainSpec, ValidationResult
    from ice_orchestrator.base_workflow import FailurePolicy

logger = get_logger(__name__)

class ChainValidator:  # – internal utility
    def __init__(
        self,
        failure_policy: "FailurePolicy",
        levels: Mapping[int, List[str]],
        nodes: Mapping[str, "NodeConfig"],
    ) -> None:
        self.failure_policy = failure_policy
        self.levels = levels
        self.nodes = nodes

    # ------------------------------------------------------------------
    # Runtime continuation logic ---------------------------------------
    # ------------------------------------------------------------------

    def should_continue(self, errors: List[str]) -> bool:
        """Determine whether chain execution should proceed after *errors*."""

        if not errors:
            return True

        if self.failure_policy.name == "HALT":  # compare by name to avoid import loops
            return False
        if self.failure_policy.name == "ALWAYS":
            return True

        # CONTINUE_POSSIBLE logic below ---------------------------------
        failed_nodes: Set[str] = set()
        for error in errors:
            if "Node " in error and " failed:" in error:
                try:
                    node_id = error.split("Node ")[1].split(" failed:")[0]
                    failed_nodes.add(node_id)
                except (IndexError, AttributeError):
                    continue

        for level_num in sorted(self.levels.keys()):
            for node_id in self.levels[level_num]:
                node = self.nodes[node_id]
                if node_id in failed_nodes:
                    continue
                depends_on_failed_node = any(
                    dep in failed_nodes for dep in getattr(node, "dependencies", [])
                )
                if not depends_on_failed_node:
                    logger.info(
                        "Chain execution continuing: Node '%s' can still execute independently",
                        node_id,
                    )
                    return True

        logger.warning(
            "Chain execution stopping: All remaining nodes depend on failed nodes: %s",
            failed_nodes,
        )
        return False

    # ------------------------------------------------------------------
    # Static validations (pre-flight) -----------------------------------
    # ------------------------------------------------------------------

    def validate_node_versions(self) -> List[str]:
        errs: List[str] = []
        for node in self.nodes.values():
            version = getattr(node, "version", None)
            if version is None and getattr(node, "metadata", None):
                version = getattr(node.metadata, "version", None)
            if not version:
                errs.append(f"Node '{node.id}' is missing version metadata.")
        return errs

    def check_license_compliance(self) -> List[str]:
        # TODO(issue-123): Implement SBOM scanning & license validation
        return []

    def detect_sensitive_data_flows(self) -> List[str]:
        # TODO(issue-124): Integrate with privacy analysis engine
        return []

    # ------------------------------------------------------------------
    # Prompt placeholder validation ------------------------------------
    # ------------------------------------------------------------------

    _PLACEHOLDER_REGEX = r"\{\s*([a-zA-Z0-9_\.]+?)\s*\}"

    def _extract_placeholders(self, template: str) -> set[str]:
        import re

        return set(re.findall(self._PLACEHOLDER_REGEX, template))

    def validate_prompt_placeholders(self) -> List[str]:
        """Ensure every `{placeholder}` appearing in a prompt is resolvable.

        A placeholder is *resolvable* when it is provided via:
        * ``input_mappings`` keys
        * ``input_selection`` (explicit pass-through from context)
        """

        errors: List[str] = []
        from ice_core.models.node_models import LLMOperatorConfig

        for node in self.nodes.values():
            if not isinstance(node, LLMOperatorConfig):
                continue  # Only AI nodes have prompts

            tmpl: str = getattr(node, "prompt", "") or ""
            if not tmpl:
                continue

            ph_set = self._extract_placeholders(tmpl)
            if not ph_set:
                continue

            available_keys = set(node.input_mappings.keys()) | set(
                (node.input_selection or [])
            )

            missing = ph_set - available_keys
            if missing:
                errors.append(
                    f"Node '{node.id}' prompt references undefined placeholders: {sorted(missing)}"
                )

        return errors

    # ------------------------------------------------------------------
    # Enhanced Chain Validator -----------------------------------------
    # ------------------------------------------------------------------

    # Legacy (advanced) validator kept under new name to avoid symbol clash ----
    def validate_chain_advanced(self, chain: "ChainSpec") -> "ValidationResult":  # type: ignore[name-defined]
        """Enhanced validation using context registry and tool schemas.

        Retained for backward-compat; prefer :meth:`validate_chain`.
        """

        errors = []
        context_keys = set()

        for node in chain.nodes:  # type: ignore[attr-defined]
            # Get tool metadata lazily to avoid heavy imports when unused
            from ice_core.models.tool import get_skill_class  # local import

            skill_cls = get_skill_class(node.type)
            input_schema = skill_cls.get_input_schema()

            # Check 1: Input context availability
            for input_key in node.inputs:  # type: ignore[attr-defined]
                if input_key not in context_keys:
                    if not context_type_manager.get_compatible_keys(input_schema):
                        errors.append(
                            f"Missing context key '{input_key}' for {node.type} inputs"
                        )

            # Check 2: Output context registration
            output_schema = skill_cls.get_output_schema()
            context_type_manager.register_context_key(node.output_key, output_schema)  # type: ignore[arg-type]
            context_keys.add(node.output_key)  # type: ignore[arg-type]

            # Check 3: Side-effect validation
            if skill_cls.is_pure() and getattr(node, "side_effects", None):
                errors.append(f"Pure tool {node.type} cannot have side-effects")

        # Use ValidationResult dataclass from legacy namespace when available
        try:
            from ice_core.models.script_chain import ValidationResult  # type: ignore

            return ValidationResult(is_valid=len(errors) == 0, errors=errors)
        except Exception:  # pragma: no cover – fallback minimal structure
            return type(
                "_ValidationResult",
                (),
                {  # – dynamic stub
                    "is_valid": len(errors) == 0,
                    "errors": errors,
                },
            )()

    def suggest_fixes(self, result: ValidationResult) -> list[str]:
        """AI-friendly fix suggestions using context registry."""
        fixes = []
        for error in result.errors:
            if "Missing context key" in error:
                key = error.split("'")[1]
                candidates = context_type_manager.get_compatible_keys(
                    {"type": "string"}  # Simplified example
                )
                fixes.append(
                    f"Replace '{key}' with similar keys: {', '.join(candidates)}"
                )
        return fixes

    # ------------------------------------------------------------------
    # Aggregated helper -------------------------------------------------
    # ------------------------------------------------------------------

    def validate_chain(self) -> List[str]:
        """Run static validations and return aggregated error list."""
        errors: List[str] = []
        errors.extend(self.validate_node_versions())
        errors.extend(self.validate_prompt_placeholders())
        errors.extend(self.check_license_compliance())
        errors.extend(self.detect_sensitive_data_flows())
        return errors
