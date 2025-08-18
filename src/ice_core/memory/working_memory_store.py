"""Working memory implementation for short-term agent state."""

import asyncio
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ice_core.costs import TokenCostCalculator
from ice_core.metrics import MEMORY_COST_TOTAL, MEMORY_TOKEN_TOTAL
from ice_core.models.enums import MemoryGuarantee
from ice_core.utils.token_counter import TokenCounter

from .base import BaseMemory, MemoryConfig, MemoryEntry


class WorkingMemory(BaseMemory):
    """In-memory working memory for short-term agent state.

    This is designed for temporary storage during agent reasoning cycles.
    It automatically expires old entries based on TTL and enforces size limits.

    Use cases:
    - Current conversation context
    - Temporary calculation results
    - Active task state
    - Short-term goals and plans
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        """Initialize working memory.

        Args:
            config: Optional configuration, defaults to memory backend
        """
        if config is None:
            config = MemoryConfig(backend="memory", ttl_seconds=300)
        super().__init__(config)

        # Use OrderedDict to maintain insertion order for LRU
        self._store: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._cleanup_task: Optional[asyncio.Task[None]] = None

        # Accounting totals
        self._token_total: int = 0
        self._cost_total: float = 0.0

    # ------------------------------------------------------------------
    # Guarantee implementation
    # ------------------------------------------------------------------

    def guarantees(self) -> set[MemoryGuarantee]:  # noqa: D401
        return {MemoryGuarantee.EPHEMERAL}

    async def initialize(self) -> None:
        """Initialize and start cleanup task."""
        self._initialized = True
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but keep running
                pass

    async def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        if not self.config.ttl_seconds:
            return

        now = datetime.utcnow()
        expired_keys = []

        for key, entry in self._store.items():
            age = (now - entry.timestamp).total_seconds()
            if age > self.config.ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self._store[key]

    def _enforce_size_limit(self) -> None:
        """Enforce maximum entry limit using LRU eviction."""
        if not self.config.max_entries:
            return

        while len(self._store) > self.config.max_entries:
            # Remove oldest (first) item
            self._store.popitem(last=False)

    async def store(
        self, key: str, content: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store content in working memory.

        Args:
            key: Unique identifier
            content: Content to store
            metadata: Optional metadata
        """
        # ------------------------------------------------------------------
        # Token and cost accounting
        # ------------------------------------------------------------------
        token_usage = 0
        if isinstance(content, str):
            try:
                # Rough estimate using OpenAI tokenizer defaults
                token_usage = TokenCounter.estimate_tokens(
                    content, model="gpt-3.5-turbo"
                )
            except Exception:
                token_usage = len(content) // 4  # Fallback heuristic
        calculator = TokenCostCalculator()
        cost_usd = calculator.calculate_cost(
            model="gpt-3.5-turbo", input_tokens=token_usage, output_tokens=0
        )

        entry = MemoryEntry(
            key=key,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
            token_usage=token_usage,
            cost_usd=cost_usd,
        )

        # Update or add entry (moves to end if exists)
        if key in self._store:
            del self._store[key]
        self._store[key] = entry

        # Update aggregate stats
        self._token_total += token_usage
        self._cost_total += cost_usd

        # Prometheus metrics
        MEMORY_TOKEN_TOTAL.labels(memory_type="working").inc(token_usage)
        MEMORY_COST_TOTAL.labels(memory_type="working").inc(cost_usd)

        # Enforce size limit
        self._enforce_size_limit()

    async def retrieve(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve entry from working memory.

        Args:
            key: Key to retrieve

        Returns:
            Memory entry if found and not expired
        """
        entry = self._store.get(key)
        if not entry:
            return None

        # Check if expired
        if self.config.ttl_seconds:
            age = (datetime.utcnow() - entry.timestamp).total_seconds()
            if age > self.config.ttl_seconds:
                del self._store[key]
                return None

        # Update access count and move to end (LRU)
        entry.access_count += 1
        del self._store[key]
        self._store[key] = entry

        return entry

    async def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search working memory by substring match.

        Args:
            query: Text to search for in content
            limit: Maximum results
            filters: Optional metadata filters

        Returns:
            Matching entries
        """
        results = []

        for entry in self._store.values():
            # Skip expired
            if self.config.ttl_seconds:
                age = (datetime.utcnow() - entry.timestamp).total_seconds()
                if age > self.config.ttl_seconds:
                    continue

            # Check query match
            content_str = str(entry.content)
            if query.lower() not in content_str.lower():
                continue

            # Check filters
            if filters:
                match = all(entry.metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    async def delete(self, key: str) -> bool:
        """Delete entry from working memory.

        Args:
            key: Key to delete

        Returns:
            True if deleted
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear entries matching pattern.

        Args:
            pattern: Optional prefix pattern

        Returns:
            Number cleared
        """
        if not pattern:
            count = len(self._store)
            self._store.clear()
            return count

        # Clear by prefix
        keys_to_delete = [k for k in self._store.keys() if k.startswith(pattern)]

        for key in keys_to_delete:
            del self._store[key]

        return len(keys_to_delete)

    async def list_keys(
        self, pattern: Optional[str] = None, limit: int = 100
    ) -> List[str]:
        """List keys in working memory.

        Args:
            pattern: Optional prefix pattern
            limit: Maximum keys to return

        Returns:
            List of keys
        """
        keys = []

        for key in self._store.keys():
            if pattern and not key.startswith(pattern):
                continue
            keys.append(key)
            if len(keys) >= limit:
                break

        return keys

    # ------------------------------------------------------------------
    # Usage statistics
    # ------------------------------------------------------------------
    def get_usage_stats(self) -> Dict[str, float]:
        """Return cumulative token and cost usage for this working memory."""
        return {"tokens": self._token_total, "cost_usd": self._cost_total}

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Clean up on exit."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
