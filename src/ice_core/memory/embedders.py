from __future__ import annotations

import hashlib
import os

try:  # Optional dependency; loaded via extras
    import openai  # type: ignore
except Exception:  # pragma: no cover - optional
    openai = None


class HashEmbedder:
    """Deterministic, offline fallback embedder for tests/dev."""

    def __init__(self, dim: int = 1536) -> None:
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        content_str = text
        h = hashlib.sha512(content_str.encode()).digest()
        # Repeat/truncate to dimension
        vals: list[float] = []
        while len(vals) < self.dim:
            vals.extend([b / 255.0 for b in h])
        vals = vals[: self.dim]
        # L2 normalize
        norm = (sum(x * x for x in vals) ** 0.5) or 1.0
        return [x / norm for x in vals]


class OpenAIEmbedder:
    """OpenAI embedding adapter using text-embedding-3-small by default."""

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        self.model = model
        if openai is None:
            raise RuntimeError("openai client not installed")
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set")

    async def embed(self, text: str) -> list[float]:
        client = openai.OpenAI()  # type: ignore[attr-defined]
        resp = client.embeddings.create(model=self.model, input=text)  # type: ignore[no-untyped-call]
        vec = resp.data[0].embedding  # type: ignore[index]
        # Trust API to return normalized floats
        return [float(x) for x in vec]


def get_embedder_from_env():
    """Return OpenAIEmbedder if configured, else HashEmbedder.

    - ICEOS_EMBEDDINGS_PROVIDER=openai and OPENAI_API_KEY present -> OpenAIEmbedder
    - Otherwise -> HashEmbedder(dim=ICEOS_EMBEDDINGS_DIM or 1536)
    """
    provider = os.getenv("ICEOS_EMBEDDINGS_PROVIDER", "hash").lower()
    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        model = os.getenv("ICEOS_EMBEDDINGS_MODEL", "text-embedding-3-small")
        try:
            return OpenAIEmbedder(model=model)
        except Exception:
            pass
    try:
        dim = int(os.getenv("ICEOS_EMBEDDINGS_DIM", "1536"))
    except Exception:
        dim = 1536
    return HashEmbedder(dim=dim)
