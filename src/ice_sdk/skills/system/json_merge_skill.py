from __future__ import annotations

from typing import Any, Dict, List

from ...utils.errors import SkillExecutionError
from ..base import SkillBase

__all__ = ["JSONMergeSkill"]


class JSONMergeSkill(SkillBase):
    """Deep-merge a list of JSON objects (dicts)."""

    name: str = "json_merge"
    description: str = "Deep-merge multiple JSON documents."
    tags: List[str] = ["json", "merge", "utility"]

    def get_required_config(self) -> list[str]:  # noqa: D401
        return []

    # Internal helper
    @staticmethod
    def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        out = a.copy()
        for k, v in b.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = JSONMergeSkill._deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    async def _execute_impl(
        self,
        *,
        docs: List[Dict[str, Any]] | None = None,
        input_data: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        # Back-compat: allow payload wrapped under *input_data* as before.
        if docs is None and input_data is not None:
            docs = input_data.get("docs")  # type: ignore[assignment]

        if not isinstance(docs, list):
            raise SkillExecutionError("'docs' must be a list of JSON objects")

        merged: Dict[str, Any] = {}
        for idx, doc in enumerate(docs):
            if not isinstance(doc, dict):
                raise SkillExecutionError(f"docs[{idx}] is not an object")
            merged = self._deep_merge(merged, doc)

        return {"merged": merged}
