from datetime import datetime
from typing import Any, Dict


class ChainMetrics:
    """
    Encapsulates metrics collection and reporting for ScriptChain.
    Tracks total tokens, node execution times, provider usage, and token usage by model.
    """

    def __init__(self, chain_name: str):
        self.metrics = {
            "total_tokens": 0,
            "node_execution_times": {},
            "provider_usage": {},
            "token_usage": {},
            "chain_name": chain_name,
        }

    def update(self, node_id: str, result: Any) -> None:
        if hasattr(result, "usage") and result.usage:
            self.metrics["total_tokens"] += result.usage.total_tokens
            provider = getattr(result.metadata, "provider", None)
            if provider not in self.metrics["provider_usage"]:
                self.metrics["provider_usage"][provider] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            self.metrics["provider_usage"][provider][
                "prompt_tokens"
            ] += result.usage.prompt_tokens
            self.metrics["provider_usage"][provider][
                "completion_tokens"
            ] += result.usage.completion_tokens
            self.metrics["provider_usage"][provider][
                "total_tokens"
            ] += result.usage.total_tokens
            model = getattr(result.usage, "model", None)
            if model not in self.metrics["token_usage"]:
                self.metrics["token_usage"][model] = 0
            self.metrics["token_usage"][model] += result.usage.total_tokens
        self.metrics["node_execution_times"][node_id] = datetime.utcnow()

    def as_dict(self) -> Dict[str, Any]:
        return self.metrics
