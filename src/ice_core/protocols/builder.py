"""Builder protocols: contracts for the AI co‑builder components.

All protocols expose an idempotent validate() method and raise typed
domain exceptions only. Implementations live in ``ice_builder``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field
from typing_extensions import runtime_checkable

from ice_core.exceptions import ValidationError
from ice_core.models.llm import LLMConfig
from ice_core.models.mcp import PartialBlueprint, PartialNodeSpec


class NodePatch(BaseModel):
    """A minimal, declarative mutation to a partial blueprint.

    This captures add/remove/update operations in a way that can be validated
    without executing any code.
    """

    action: str = Field(..., description="add_node | remove_node | update_node")
    node: Optional[PartialNodeSpec] = None
    node_id: Optional[str] = None
    updates: Optional[Dict[str, Any]] = None

    def ensure_valid(self) -> None:
        if self.action not in {"add_node", "remove_node", "update_node"}:
            raise ValidationError(f"Unsupported node patch action: {self.action}")
        if self.action == "add_node" and self.node is None:
            raise ValidationError("add_node requires 'node'")
        if self.action in {"remove_node", "update_node"} and not self.node_id:
            raise ValidationError(f"{self.action} requires 'node_id'")


@runtime_checkable
class PlannerProtocol(Protocol):
    """Plan nodes from natural language and canvas state."""

    def validate(self) -> None:  # pragma: no cover – trivial
        ...

    async def plan(
        self, *, text: str, canvas_state: Dict[str, Any]
    ) -> List[NodePatch]: ...


@runtime_checkable
class RetrieverProtocol(Protocol):
    """Retrieve design-time context for planning."""

    def validate(self) -> None:  # pragma: no cover
        ...

    async def get_context(
        self, *, query: str, scopes: List[str]
    ) -> Dict[str, Any]:  # library, blueprints, runs, schemas
        ...


@runtime_checkable
class RankerProtocol(Protocol):
    def validate(self) -> None:  # pragma: no cover
        ...

    async def rank(
        self, *, options: List[Dict[str, Any]], criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]: ...


@runtime_checkable
class CriticProtocol(Protocol):
    def validate(self) -> None:  # pragma: no cover
        ...

    async def review(
        self, *, blueprint: Dict[str, Any], run_logs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]: ...


@runtime_checkable
class PatchApplierProtocol(Protocol):
    def validate(self) -> None:  # pragma: no cover
        ...

    async def validate_and_apply(
        self, *, blueprint: PartialBlueprint, patches: List[NodePatch]
    ) -> PartialBlueprint: ...


@runtime_checkable
class ModelPolicyProtocol(Protocol):
    def validate(self) -> None:  # pragma: no cover
        ...

    def select(self, *, task: str, constraints: Dict[str, Any]) -> LLMConfig: ...


@runtime_checkable
class ToolSchemaProviderProtocol(Protocol):
    def validate(self) -> None:  # pragma: no cover
        ...

    async def list(self) -> List[Dict[str, Any]]: ...


@runtime_checkable
class DraftStoreProtocol(Protocol):
    def validate(self) -> None:  # pragma: no cover
        ...

    async def put(self, *, key: str, value: Dict[str, Any]) -> None: ...

    async def get(self, *, key: str) -> Optional[Dict[str, Any]]: ...


__all__ = [
    "NodePatch",
    "PlannerProtocol",
    "RetrieverProtocol",
    "RankerProtocol",
    "CriticProtocol",
    "PatchApplierProtocol",
    "ModelPolicyProtocol",
    "ToolSchemaProviderProtocol",
    "DraftStoreProtocol",
]
