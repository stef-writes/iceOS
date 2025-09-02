from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel

from ice_core.llm.service import LLMService
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.protocols.builder import CriticProtocol


class CriticPromptPack(BaseModel):
    system: str
    user_template: str


def default_critic_pack() -> CriticPromptPack:
    return CriticPromptPack(
        system=(
            "You are a rigorous reviewer of workflow blueprints.\n"
            "Given a blueprint JSON and optional run logs, list issues and suggested fixes.\n"
            'Output STRICT JSON: {"issues":[], "fixes":[], "confidence": 0-1}.\n'
            "No prose."
        ),
        user_template=(
            "Blueprint JSON:\n{blueprint}\n\nRun logs (optional):\n{run_logs}\n"
        ),
    )


class PromptCritic(CriticProtocol):
    def __init__(
        self, *, llm: LLMService | None = None, pack: CriticPromptPack | None = None
    ) -> None:
        self._llm = llm or LLMService()
        self._pack = pack or default_critic_pack()

    def validate(self) -> None:
        return None

    async def review(
        self, *, blueprint: Dict[str, Any], run_logs: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        # Best-effort LLM call; return empty structure on failure to keep deterministic
        prompt = (
            self._pack.system
            + "\n\n"
            + self._pack.user_template.format(
                blueprint=blueprint, run_logs=run_logs or {}
            )
        )
        cfg = LLMConfig(provider=ModelProvider.OPENAI, model="gpt-4o", temperature=0)
        text, _usage, err = await self._llm.generate(
            llm_config=cfg, prompt=prompt, context={}
        )
        if err or not text:
            return {"issues": [], "fixes": [], "confidence": 0.0}
        try:
            import json

            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("critic non-dict output")
            # minimal sanitation
            data.setdefault("issues", [])
            data.setdefault("fixes", [])
            data.setdefault("confidence", 0.0)
            return data
        except Exception:
            return {"issues": [], "fixes": [], "confidence": 0.0}


__all__ = ["CriticPromptPack", "default_critic_pack", "PromptCritic"]
