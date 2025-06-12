"""Simple pluggable artifact store.

This module was moved from ``app.core`` to ``app.utils`` to keep all general-purpose
helpers in one place and avoid an extra package hop.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

__all__ = ["ArtifactRef", "ArtifactStore", "LocalArtifactStore"]


class ArtifactRef(str):
    """Opaque reference string returned by :py:meth:`ArtifactStore.put`."""


class ArtifactStore:
    """Abstract base class for an artifact store."""

    def put(self, obj: Any) -> ArtifactRef:  # noqa: D401
        raise NotImplementedError

    def get(self, ref: ArtifactRef) -> Any:  # noqa: D401
        raise NotImplementedError


class LocalArtifactStore(ArtifactStore):
    """Naive implementation that serialises JSON blobs to a local directory."""

    def __init__(self, root_dir: str | Path = ".artifacts"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def put(self, obj: Any) -> ArtifactRef:  # noqa: D401
        artifact_id = uuid.uuid4().hex
        path = self.root_dir / f"{artifact_id}.json"
        with path.open("w", encoding="utf-8") as fp:
            json.dump(obj, fp, ensure_ascii=False, indent=2, default=str)
        return ArtifactRef(artifact_id)

    def get(self, ref: ArtifactRef) -> Any:  # noqa: D401
        path = self.root_dir / f"{ref}.json"
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {ref}")
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
