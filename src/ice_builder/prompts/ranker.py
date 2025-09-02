from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel

from ice_core.llm.service import LLMService
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.protocols.builder import RankerProtocol


class RankerPromptPack(BaseModel):
    system: str
    user_template: str


def default_ranker_pack() -> RankerPromptPack:
    return RankerPromptPack(
        system=(
            "You are a ranking assistant. Rank alternatives from best to worst based on the criteria.\n"
            "Output STRICT JSON array of indices (0-based) in ranked order.\n"
        ),
        user_template=("Options JSON:\n{options}\n\nCriteria JSON:\n{criteria}\n"),
    )


class PromptRanker(RankerProtocol):
    def __init__(
        self, *, llm: LLMService | None = None, pack: RankerPromptPack | None = None
    ) -> None:
        self._llm = llm or LLMService()
        self._pack = pack or default_ranker_pack()

    def validate(self) -> None:
        return None

    async def rank(
        self, *, options: List[Dict[str, Any]], criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        prompt = (
            self._pack.system
            + "\n\n"
            + self._pack.user_template.format(options=options, criteria=criteria)
        )
        cfg = LLMConfig(provider=ModelProvider.OPENAI, model="gpt-4o", temperature=0)
        text, _usage, err = await self._llm.generate(
            llm_config=cfg, prompt=prompt, context={}
        )
        if err or not text:
            return options
        try:
            import json

            idxs = json.loads(text)
            if not isinstance(idxs, list):
                raise ValueError("ranker non-list output")
            ranked = []
            for i in idxs:
                try:
                    ranked.append(options[int(i)])
                except Exception:
                    pass
            # Keep any missing options appended at the end
            seen = set(idxs)
            for j, opt in enumerate(options):
                if j not in seen:
                    ranked.append(opt)
            return ranked
        except Exception:
            return options


__all__ = ["RankerPromptPack", "default_ranker_pack", "PromptRanker"]
