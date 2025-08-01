from __future__ import annotations

"""Builder utility for composing *network* manifest files.

This intentionally lives in the **SDK layer** so application code (or Frosty)
can generate manifests without importing the orchestrator layer.

The builder is deliberately minimal: it only knows how to build a dict and—to
make life easy—write it out as YAML/JSON. Validation is deferred to
NetworkCoordinator when the manifest is executed.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

__all__ = ["NetworkBuilder"]


class NetworkBuilder:
    """Fluent API for crafting a network manifest.

    Example
    -------
    >>> nb = (NetworkBuilder("nightly_stack")
    ...       .set_global(budget_usd=5, memory_backend="redis://prod/4")
    ...       .add_workflow("etl:create_etl_workflow", id="etl")
    ...       .add_workflow("training:create_training", after="etl"))
    >>> nb.write("nightly.yml")
    """

    def __init__(self, name: str, *, api_version: str = "network.v0") -> None:
        self._manifest: Dict[str, Any] = {
            "api_version": api_version,
            "name": name,
            "workflows": [],
        }

    # ------------------------------------------------------------------
    # Fluent setters                                                     
    # ------------------------------------------------------------------

    def set_global(self, **config: Any) -> "NetworkBuilder":
        """Set top-level ``global`` config overrides."""
        self._manifest.setdefault("global", {}).update(config)
        return self

    def add_workflow(
        self,
        ref: str,
        *,
        id: Optional[str] = None,
        after: Optional[str] = None,
        schedule: Optional[str] = None,
        **extra: Any,
    ) -> "NetworkBuilder":
        """Append a workflow reference.

        Parameters
        ----------
        ref: str
            Import path (``module[:attr]``) that resolves to a Workflow.
        id: str, optional
            Identifier used for dependencies. Defaults to *ref*.
        after: str, optional
            ID of the workflow that must finish before this one starts.
        schedule: str, optional
            Cron expression ("0 2 * * *") for scheduled execution.
        extra: Any
            Additional free-form fields preserved in the manifest.
        """
        entry: Dict[str, Any] = {"ref": ref}
        if id:
            entry["id"] = id
        if after:
            entry["after"] = after
        if schedule:
            entry["schedule"] = schedule
        if extra:
            entry.update(extra)
        self._manifest["workflows"].append(entry)
        return self

    # ------------------------------------------------------------------
    # Output helpers                                                     
    # ------------------------------------------------------------------

    def build(self) -> Dict[str, Any]:
        """Return the manifest dict (deep copy)."""
        import copy

        return copy.deepcopy(self._manifest)

    def write(self, path: str | Path, *, fmt: str | None = None) -> Path:
        """Write manifest to *path* (YAML by extension or *fmt*).

        Args
        ----
        path: str | Path
            Output file path (".yml", ".yaml" or ".json").
        fmt: str, optional
            Override format ("yaml" or "json").  When omitted, the extension of
            *path* determines the encoding.
        """
        path = Path(path)
        format_hint = fmt or path.suffix.lstrip(".").lower()
        data = self.build()
        if format_hint in {"yaml", "yml"}:
            path.write_text(yaml.safe_dump(data, sort_keys=False))
        elif format_hint == "json":
            path.write_text(json.dumps(data, indent=2))
        else:
            raise ValueError("Unsupported format – use yaml|yml|json or specify fmt param")
        return path 