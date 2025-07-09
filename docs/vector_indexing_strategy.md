# Vector Embeddings, Indexing & Hashing — Final Architecture (v1.0.0)

> **Status:** Draft – Approved by Tech Lead & Stakeholders (2025-07-09)

This document consolidates the original proposal, stakeholder feedback, and the alignment session.  It is the single source of truth for how iceOS handles embeddings, vector search, and hashing going forward.

---

## 1. Guiding Principles

1. *Build the core, plug-in the rest.*  We own the primary path; external services act only as graceful degradation.
2. *Pluggability everywhere.*  Every moving piece (embedder, index, hashing) must be swappable via dependency-injection and runtime config.
3. *Cost & compliance first.*  All external calls go through `BudgetEnforcer`; hashing defaults to SHA-256 for auditability.

---

## 2. Embedding Service

| Concern                | Decision                                                                           |
|------------------------|------------------------------------------------------------------------------------|
| Primary model          | `SentenceTransformer('all-MiniLM-L6-v2')` (local, CPU/GPU)                          |
| Fallback providers     | AWS Titan, Cohere, OpenAI – accessed through **provider router**                    |
| Routing order          | Local → Provider 1 → Provider 2 … (configurable)                                    |
| Budget enforcement     | All cloud calls wrap `BudgetEnforcer.check(cost)`                                   |
| Interface              | `IEmbedder` with async `embed(text: str) -> Embedding`                              |

### 2.1 Reference Implementation

```python
from sentence_transformers import SentenceTransformer
from ice_sdk.providers.llm_service import TitanService, CohereService
from ice_sdk.providers.budget_enforcer import BudgetEnforcer
from ice_sdk.models.embedding import Embedding

class HybridEmbedder:
    """Route embedding requests to local or cloud providers."""

    def __init__(self) -> None:
        self._local = SentenceTransformer("all-MiniLM-L6-v2")
        self._providers = [TitanService(), CohereService()]

    async def embed(self, text: str) -> Embedding:
        try:
            return Embedding.vector(self._local.encode(text))  # primary path
        except Exception:
            for prov in self._providers:
                cost = prov.estimate(text)
                BudgetEnforcer.check(cost)
                try:
                    return await prov.embed(text)
                except Exception:
                    continue
            raise RuntimeError("All embedding providers failed")
```

---

## 3. Vector Index / Database Layer

| Concern                 | Decision                                                                           |
|-------------------------|------------------------------------------------------------------------------------|
| Default implementation  | **ChromaDBAdapter** (backwards-compat with existing PoCs)                          |
| Alt. in-process index   | `AnnoyIndex`, `hnswlib` via `HNSWAdapter`                                          |
| Interface               | `IVectorIndex` with async CRUD + `query()`                                         |
| Storage backends        | SQLite (lightweight) / Postgres (prod) – driven by Chroma’s setting                |
| Swap mechanism          | Provider name in `chains.toml` or env `ICE_INDEX_PROVIDER`                         |

### 3.1 Adapter Skeleton

```python
class ChromaDBAdapter(IVectorIndex):
    def __init__(self, client: "ChromaClient") -> None:
        self._client = client

    async def upsert(self, key: str, embedding: list[float]) -> None:
        await self._client.add(id=key, embedding=embedding)

    async def query(self, embedding: list[float], k: int = 5):
        return await self._client.query(embedding, n_results=k)
```

---

## 4. Hashing & Deduplication

| Concern             | Decision                                                      |
|---------------------|---------------------------------------------------------------|
| Compliance default  | **SHA-256**                                                   |
| Performance mode    | **BLAKE3** (AVX-accelerated)                                  |
| Semantic mode       | **MinHash + embedding similarity** for near-dup detection      |
| Config toggle       | `hash.mode = [security | performance | semantic]`             |

### 4.1 Configurable Hasher

```python
from hashlib import sha256
from blake3 import blake3

class HashMode(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    SEMANTIC = "semantic"

async def compute_hash(content: str, mode: HashMode = HashMode.SECURITY) -> str:
    if mode == HashMode.SECURITY:
        return sha256(content.encode()).hexdigest()
    if mode == HashMode.PERFORMANCE:
        return blake3(content.encode()).hexdigest()
    # semantic → returns MinHash signature (pseudo-code)
    sig = await get_minhash_signature(content)
    return sig.hex()
```

---

## 5. Build-vs-Buy Matrix

| Capability        | Build (iceOS)                               | Buy / External                            | Rationale                                          |
|-------------------|---------------------------------------------|-------------------------------------------|----------------------------------------------------|
| Embedding (primary)| Local `SentenceTransformer`                 | Titan, Cohere (fallback)                  | Cost-control & latency                             |
| Vector DB          | Chroma (open-source)                        | Pinecone, Weaviate (future if needed)     | Avoid vendor lock-in; keep open-core               |
| Hashing            | Built-in SHA-256/BLAKE3/MinHash             | –                                         | Keeps auditability internal                        |

---

## 6. Configuration Defaults

```toml
# chains.toml
[index]
provider = "chroma"  # or "annoy", "hnsw"

[embedding]
router_order = ["local", "titan", "cohere"]
budget_cap_usd = 5.00

[hash]
mode = "security"
```

---

## 7. Risks & Mitigations

| Risk                                   | Mitigation                                                            |
|----------------------------------------|-----------------------------------------------------------------------|
| Cloud embedding over-spend             | Real-time check via `BudgetEnforcer`; per-session cost ceiling        |
| Index provider drift                   | CI step runs contract tests against all `IVectorIndex` implementations|
| Hash-mode mis-configuration            | Runtime warning + telemetry event when non-SHA mode is used          |

---

## 8. Deliverables & Timeline

1. `HybridEmbedder` + provider router – **ETA: 2 weeks**
2. `IVectorIndex` + Chroma & Annoy adapters – **ETA: 3 weeks**
3. Configurable Hasher utility – **ETA: 1 week**
4. Contract tests & CI integration – **ETA: 1 week**

Total: **4 weeks** to merge into `main` before Q3 “Runtime GA” freeze.

---

> Maintainers: update this doc on every material change and bump the header version. 