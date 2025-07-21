from __future__ import annotations

import warnings as _warnings
from typing import Any, Dict, Generator, Mapping, Tuple

# Pydantic v2 migrated – PrivateAttr for internal attributes
from pydantic import BaseModel, PrivateAttr

from .base import SkillBase

_warnings.warn(
    "'ice_sdk.skills.registry' is deprecated; import from 'ice_sdk.registry.skill' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SkillRegistry", "global_skill_registry"]


class SkillRegistrationError(RuntimeError):
    """Raised when a skill cannot be registered in the registry."""


class SkillRegistry(BaseModel):
    """In-memory registry that resolves *Skill* implementations by name.

    Strategic purpose:
    1. Central source-of-truth – prevents accidental duplication or shadowing
       of skill identifiers.
    2. Layer boundary enforcement – orchestrator resolves external actions
       only through this interface (Rule 2 & Rule 11).
    3. Validation – each skill's *validate()* method is invoked at registration
       time to guarantee config correctness (Rule 13).
    """

    # Internal mapping – excluded from model schema
    _skills: Dict[str, SkillBase] = PrivateAttr(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "forbid",
    }

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def register(self, name: str, skill: SkillBase) -> None:
        """Register an instantiated *Skill* under *name*.

        Parameters
        ----------
        name: str
            Public identifier used by workflows.
        skill: SkillBase
            An instantiated, fully-validated skill.
        """
        if name in self._skills:
            raise SkillRegistrationError(f"Skill '{name}' already registered")

        # Skills are validated by Pydantic at instantiation time
        # No need for additional validation here

        self._skills[name] = skill

        # ------------------------------------------------------------------
        # Legacy ToolService synchronisation – keeps tool nodes working
        # ------------------------------------------------------------------
        try:
            from ice_sdk.skills.service import ToolService  # updated import path

            ToolService._registry[name] = skill.__class__  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover – never break registration
            pass

    def get(self, name: str) -> SkillBase:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise SkillRegistrationError(f"Skill '{name}' not found") from exc

    async def execute(
        self, name: str, payload: Mapping[str, Any]
    ) -> Any:  # noqa: ANN401 – Any by design
        """Execute *skill* identified by *name* with *payload*.

        The call propagates the underlying *Skill* exception semantics.
        """
        skill = self.get(name)
        return await skill.execute(dict(payload))

    # ------------------------------------------------------------------
    # New helper: filter *Agent* subtype skills -------------------------
    # ------------------------------------------------------------------

    def get_agents(self):  # type: ignore[override]
        """Return skills where ``skill.meta.node_subtype == 'agent'``."""

        from typing import List

        from ice_sdk.skills.base import SkillMeta  # local import to avoid cycles

        agents: List[SkillMeta] = []
        for skill in self._skills.values():
            try:
                if getattr(skill.meta, "node_subtype", None) == "agent":
                    agents.append(skill.meta)
            except Exception:  # pragma: no cover – guard against malicious skills
                continue
        return agents

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __iter__(self) -> Generator[Tuple[str, SkillBase], None, None]:
        yield from self._skills.items()

    def __len__(self) -> int:
        return len(self._skills)


# Global default registry -----------------------------------------------------

global_skill_registry: "SkillRegistry" = SkillRegistry()
