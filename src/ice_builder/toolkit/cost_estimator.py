from __future__ import annotations

import json
import os
import time

from pydantic import BaseModel, Field, PrivateAttr

from ice_core.models.llm import LLMConfig


class CostEstimate(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    tool_calls: int = 0
    est_usd: float = 0.0


class CostEstimator(BaseModel):
    """Conservative, provider-agnostic cost estimator for planning.

    Environment-tunable via simple multipliers; callers can pass token counts
    when known, or rely on approximate heuristics based on text length.
    """

    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    usd_per_1k_prompt_tokens: float = 0.002
    usd_per_1k_completion_tokens: float = 0.004
    usd_per_1k_embedding_tokens: float = 0.0001
    usd_per_tool_call: float = 0.0005

    # Minimal per-model price table (defaults). Can be overridden via config.
    price_table: dict[str, dict[str, float]] = Field(
        default_factory=lambda: {
            "openai:gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "openai:gpt-4o-mini": {"prompt": 0.002, "completion": 0.006},
            "anthropic:claude-3-5-sonnet": {"prompt": 0.003, "completion": 0.015},
            "google:gemini-1.5-pro": {"prompt": 0.0025, "completion": 0.0075},
            "deepseek:deepseek-chat": {"prompt": 0.0007, "completion": 0.0015},
        }
    )
    cache_ttl_seconds: int = Field(default=3600)
    _cache_loaded_at: float = PrivateAttr(default=0.0)

    def estimate(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        embedding_tokens: int = 0,
        tool_calls: int = 0,
    ) -> CostEstimate:
        est = CostEstimate(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            embedding_tokens=embedding_tokens,
            tool_calls=tool_calls,
        )
        est.est_usd = (
            (prompt_tokens / 1000.0) * self.usd_per_1k_prompt_tokens
            + (completion_tokens / 1000.0) * self.usd_per_1k_completion_tokens
            + (embedding_tokens / 1000.0) * self.usd_per_1k_embedding_tokens
            + (tool_calls * self.usd_per_tool_call)
        )
        return est

    def estimate_by_model(
        self,
        *,
        provider: str | None,
        model: str | None,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        key = f"{(provider or '').lower()}:{(model or '').lower()}"
        prices = self._get_price_table().get(key)
        if not prices:
            return self.estimate(
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
            ).est_usd
        prompt_cost = (prompt_tokens / 1000.0) * float(
            prices.get("prompt", self.usd_per_1k_prompt_tokens)
        )
        completion_cost = (completion_tokens / 1000.0) * float(
            prices.get("completion", self.usd_per_1k_completion_tokens)
        )
        return prompt_cost + completion_cost

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def _get_price_table(self) -> dict[str, dict[str, float]]:
        """Return a price table, reloading from config with TTL when available.

        Config sources (first hit wins):
        - ICE_PRICING_JSON: inline JSON string mapping "provider:model" -> {prompt, completion}
        - ICE_PRICING_FILE: path to a JSON file with the same structure
        Fallback: in-memory default price_table.
        """
        now = time.time()
        if self._cache_loaded_at and now - self._cache_loaded_at < float(
            self.cache_ttl_seconds
        ):
            return self.price_table
        try:
            inline = os.getenv("ICE_PRICING_JSON")
            if inline:
                data = json.loads(inline)
                if isinstance(data, dict):
                    # Shallow validation: values are dicts with numeric fields
                    self.price_table = {
                        str(k): {
                            "prompt": float(v.get("prompt", 0.0)),
                            "completion": float(v.get("completion", 0.0)),
                        }
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
                    self._cache_loaded_at = now
                    return self.price_table
            path = os.getenv("ICE_PRICING_FILE")
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.price_table = {
                        str(k): {
                            "prompt": float(v.get("prompt", 0.0)),
                            "completion": float(v.get("completion", 0.0)),
                        }
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
                    self._cache_loaded_at = now
                    return self.price_table
        except Exception:
            # Keep defaults on any error
            pass
        self._cache_loaded_at = now
        return self.price_table
