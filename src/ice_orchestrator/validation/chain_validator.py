"""Validation helpers for ScriptChain execution.

This module centralises validation and control-flow logic that used to live
inside `script_chain.py`, improving separation of concerns and testability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Mapping, Set

from structlog import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from ice_sdk.models.node_models import NodeConfig
    from ice_sdk.orchestrator.base_workflow import FailurePolicy

logger = get_logger(__name__)


class ChainValidator:  # noqa: D101 – internal utility
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

    def _extract_placeholders(self, template: str) -> set[str]:  # noqa: D401
        import re

        return set(re.findall(self._PLACEHOLDER_REGEX, template))

    def validate_prompt_placeholders(self) -> List[str]:
        """Ensure every `{placeholder}` appearing in a prompt is resolvable.

        A placeholder is *resolvable* when it is provided via:
        * ``input_mappings`` keys
        * ``input_selection`` (explicit pass-through from context)
        """

        errors: List[str] = []
        from ice_sdk.models.node_models import LLMOperatorConfig

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
