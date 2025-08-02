"""Protocol definition for LLM providers."""
from __future__ import annotations

from abc import abstractmethod
from typing import Protocol


class LLMProvider(Protocol):
    name: str

    @abstractmethod
    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str: ...