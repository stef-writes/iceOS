"""Episodic memory for storing conversation and interaction history."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

from ice_core.costs import TokenCostCalculator
from ice_core.metrics import MEMORY_COST_TOTAL, MEMORY_TOKEN_TOTAL
from ice_core.models.enums import MemoryGuarantee
from ice_core.utils.token_counter import TokenCounter

from .base import BaseMemory, MemoryConfig, MemoryEntry

try:
    import redis
    from redis import Redis
    from redis.client import Pipeline as RedisPipeline
except ImportError:
    redis = None  # type: ignore[assignment]
    Redis = None  # type: ignore
    RedisPipeline = None  # type: ignore


class EpisodicMemory(BaseMemory):
    """Memory for storing conversation and interaction history.

    Uses Redis for persistence with support for:
    - Conversation history with customers
    - Past negotiation outcomes
    - User preferences and patterns
    - Interaction timelines
    - Semantic search through metadata
    """

    # ------------------------------------------------------------------
    # MemoryGuarantee interface
    # ------------------------------------------------------------------
    def guarantees(self) -> set[MemoryGuarantee]:  # noqa: D401
        return {MemoryGuarantee.TTL}

    def __init__(self, config: MemoryConfig):
        """Initialize episodic memory with Redis backend."""
        super().__init__(config)
        self._redis: Optional[Any] = None
        self._memory_store: Dict[str, Any] = {}  # Fallback to dict
        self._key_prefix = "episode:"
        self._index_prefix = "episode_idx:"
        self._ttl = (
            config.ttl_seconds if config.ttl_seconds else 7 * 24 * 3600
        )  # 7 days default

        # Accounting totals
        self._token_total: int = 0
        self._cost_total: float = 0.0

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        if self._initialized:
            return

        try:
            # Parse Redis connection info from config
            redis_config = self.config.connection_params or {}
            host = redis_config.get("host", "localhost")
            port = redis_config.get("port", 6379)
            db = redis_config.get("db", 0)
            password = redis_config.get("password")

            # Create Redis connection
            if redis is not None:
                self._redis = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
                )
            else:
                raise ImportError("Redis library not installed")

            # Test connection
            await self._redis.ping()
            self._initialized = True

        except Exception as e:
            # Fallback to in-memory if Redis not available
            print(f"Redis connection failed: {e}. Using in-memory storage.")
            self._redis = None
            self._memory_store = {}  # Fallback to dict
            self._initialized = True

    async def store(
        self, key: str, content: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store an episode/interaction."""
        if not self._initialized:
            await self.initialize()

        # ------------------------------------------------------------------
        # Token and cost accounting
        # ------------------------------------------------------------------
        token_usage = 0
        if isinstance(content, str):
            try:
                token_usage = TokenCounter.estimate_tokens(
                    content, model="gpt-3.5-turbo"
                )
            except Exception:
                token_usage = len(content) // 4
        calculator = TokenCostCalculator()
        cost_usd = calculator.calculate_cost(
            model="gpt-3.5-turbo", input_tokens=token_usage, output_tokens=0
        )

        # Create memory entry
        entry = MemoryEntry(
            key=key,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now(),
            token_usage=token_usage,
            cost_usd=cost_usd,
        )

        # Add episode-specific metadata
        metadata = metadata or {}  # Ensure metadata is not None
        entry.metadata.update(
            {
                "episode_type": metadata.get("type", "conversation"),
                "participants": metadata.get("participants", []),
                "outcome": metadata.get("outcome", "ongoing"),
                "sentiment": metadata.get("sentiment", "neutral"),
                "tags": metadata.get("tags", []),
            }
        )

        if self._redis:
            # Store in Redis
            full_key = f"{self._key_prefix}{key}"

            # Serialize entry
            entry_data = {
                "content": (
                    json.dumps(content) if not isinstance(content, str) else content
                ),
                "metadata": json.dumps(entry.metadata),
                "timestamp": entry.timestamp.isoformat(),
            }

            # Store with TTL
            pipeline = self._redis.pipeline()
            pipeline.hset(full_key, mapping=entry_data)
            pipeline.expire(full_key, self._ttl)

            # Index by various attributes for search
            self._index_episode(pipeline, key, entry)

            pipeline.execute()

            # Update aggregate stats
            self._token_total += token_usage
            self._cost_total += cost_usd

            # Prometheus metrics
            MEMORY_TOKEN_TOTAL.labels(memory_type="episodic").inc(token_usage)
            MEMORY_COST_TOTAL.labels(memory_type="episodic").inc(cost_usd)
        else:
            # Fallback to in-memory
            self._memory_store[key] = entry

            # Update aggregate stats
            self._token_total += token_usage
            self._cost_total += cost_usd

            # Prometheus metrics
            MEMORY_TOKEN_TOTAL.labels(memory_type="episodic").inc(token_usage)
            MEMORY_COST_TOTAL.labels(memory_type="episodic").inc(cost_usd)

    def _index_episode(self, pipeline: Any, key: str, entry: MemoryEntry) -> None:
        """Index episode for efficient search."""
        # Index by type
        episode_type = entry.metadata.get("episode_type", "unknown")
        pipeline.sadd(f"{self._index_prefix}type:{episode_type}", key)
        pipeline.expire(f"{self._index_prefix}type:{episode_type}", self._ttl)

        # Index by participants
        for participant in entry.metadata.get("participants", []):
            pipeline.sadd(f"{self._index_prefix}participant:{participant}", key)
            pipeline.expire(f"{self._index_prefix}participant:{participant}", self._ttl)

        # Index by tags
        for tag in entry.metadata.get("tags", []):
            pipeline.sadd(f"{self._index_prefix}tag:{tag}", key)
            pipeline.expire(f"{self._index_prefix}tag:{tag}", self._ttl)

        # Index by date (for time-based queries)
        date_key = entry.timestamp.strftime("%Y-%m-%d")
        pipeline.sadd(f"{self._index_prefix}date:{date_key}", key)
        pipeline.expire(f"{self._index_prefix}date:{date_key}", self._ttl)

        # Index by outcome
        outcome = entry.metadata.get("outcome", "unknown")
        pipeline.sadd(f"{self._index_prefix}outcome:{outcome}", key)
        pipeline.expire(f"{self._index_prefix}outcome:{outcome}", self._ttl)

    async def retrieve(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve a specific episode."""
        if not self._initialized:
            await self.initialize()

        if self._redis:
            full_key = f"{self._key_prefix}{key}"
            data = self._redis.hgetall(full_key)

            if not data:
                return None

            # Deserialize
            content = data.get("content", "")
            try:
                content = json.loads(content)
            except Exception:
                pass  # Keep as string if not JSON

            metadata = json.loads(data.get("metadata", "{}"))
            timestamp = datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            )

            return MemoryEntry(
                key=key, content=content, metadata=metadata, timestamp=timestamp
            )
        else:
            # Fallback to in-memory
            entry = self._memory_store.get(key)
            if entry is not None:
                return cast(MemoryEntry, entry)
            return None

    async def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search episodes by content or metadata."""
        if not self._initialized:
            await self.initialize()

        filters = filters or {}
        matching_keys = set()

        if self._redis:
            # Start with all keys if no filters
            if not filters:
                # Search by query in content (simple substring match)
                all_keys = self._redis.keys(f"{self._key_prefix}*")
                for full_key in all_keys[:100]:  # Limit scan
                    key = full_key.replace(self._key_prefix, "")
                    entry = await self.retrieve(key)
                    if entry and query.lower() in str(entry.content).lower():
                        matching_keys.add(key)
            else:
                # Use indexes for filtered search
                sets_to_intersect = []

                if "type" in filters:
                    sets_to_intersect.append(
                        f"{self._index_prefix}type:{filters['type']}"
                    )

                if "participant" in filters:
                    sets_to_intersect.append(
                        f"{self._index_prefix}participant:{filters['participant']}"
                    )

                if "tags" in filters:
                    for tag in filters["tags"]:
                        sets_to_intersect.append(f"{self._index_prefix}tag:{tag}")

                if "outcome" in filters:
                    sets_to_intersect.append(
                        f"{self._index_prefix}outcome:{filters['outcome']}"
                    )

                if "date" in filters:
                    sets_to_intersect.append(
                        f"{self._index_prefix}date:{filters['date']}"
                    )

                # Get intersection of all filter sets
                if sets_to_intersect:
                    if len(sets_to_intersect) == 1:
                        matching_keys = set(self._redis.smembers(sets_to_intersect[0]))
                    else:
                        # Create temporary key for intersection
                        temp_key = (
                            f"temp:search:{hashlib.md5(query.encode()).hexdigest()}"
                        )
                        self._redis.sinterstore(temp_key, *sets_to_intersect)
                        matching_keys = set(self._redis.smembers(temp_key))
                        self._redis.delete(temp_key)

                # Further filter by query if provided
                if query and matching_keys:
                    filtered_keys = set()
                    for key in matching_keys:
                        entry = await self.retrieve(key)
                        if (
                            entry is not None
                            and query.lower() in str(entry.content).lower()
                        ):
                            filtered_keys.add(key)
                    matching_keys = filtered_keys
        else:
            # Fallback to in-memory search
            for key, entry in self._memory_store.items():
                # Check query match
                if entry is None:
                    continue
                if query and query.lower() not in str(entry.content).lower():  # type: ignore[union-attr]
                    continue

                # Check filters
                if filters:
                    if (
                        "type" in filters
                        and entry.metadata.get("episode_type") != filters["type"]
                    ):  # type: ignore[union-attr]
                        continue
                    if "participant" in filters and filters[
                        "participant"
                    ] not in entry.metadata.get("participants", []):  # type: ignore[union-attr]
                        continue
                    if "tags" in filters:
                        entry_tags = set(entry.metadata.get("tags", []))  # type: ignore[union-attr]
                        if not all(tag in entry_tags for tag in filters["tags"]):
                            continue
                    if (
                        "outcome" in filters
                        and entry.metadata.get("outcome") != filters["outcome"]
                    ):  # type: ignore[union-attr]
                        continue

                matching_keys.add(key)

        # Retrieve matching entries
        entries = []
        for key in list(matching_keys)[:limit]:
            entry = await self.retrieve(key)
            if entry:
                entries.append(entry)

        # Sort by timestamp (most recent first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)

        return entries[:limit]

    async def delete(self, key: str) -> bool:
        """Delete an episode."""
        if not self._initialized:
            await self.initialize()

        if self._redis:
            full_key = f"{self._key_prefix}{key}"

            # Get entry for cleanup
            entry = await self.retrieve(key)
            if not entry:
                return False

            # Remove from indexes
            pipeline = self._redis.pipeline()

            # Remove from type index
            episode_type = entry.metadata.get("episode_type", "unknown")
            pipeline.srem(f"{self._index_prefix}type:{episode_type}", key)

            # Remove from participant indexes
            for participant in entry.metadata.get("participants", []):
                pipeline.srem(f"{self._index_prefix}participant:{participant}", key)

            # Remove from tag indexes
            for tag in entry.metadata.get("tags", []):
                pipeline.srem(f"{self._index_prefix}tag:{tag}", key)

            # Remove from date index
            date_key = entry.timestamp.strftime("%Y-%m-%d")
            pipeline.srem(f"{self._index_prefix}date:{date_key}", key)

            # Remove from outcome index
            outcome = entry.metadata.get("outcome", "unknown")
            pipeline.srem(f"{self._index_prefix}outcome:{outcome}", key)

            # Delete the entry
            pipeline.delete(full_key)

            results = pipeline.execute()
            return bool(results[-1] > 0)  # Check if delete was successful
        else:
            # Fallback to in-memory
            return self._memory_store.pop(key, None) is not None

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear episodes matching pattern."""
        if not self._initialized:
            await self.initialize()

        count = 0

        if self._redis:
            if pattern:
                # Clear by pattern
                keys = self._redis.keys(f"{self._key_prefix}{pattern}*")
                for full_key in keys:
                    key = full_key.replace(self._key_prefix, "")
                    if await self.delete(key):
                        count += 1
            else:
                # Clear all episodes
                keys = self._redis.keys(f"{self._key_prefix}*")
                pipeline = self._redis.pipeline()
                for key in keys:
                    pipeline.delete(key)
                    count += 1

                # Clear all indexes
                index_keys = self._redis.keys(f"{self._index_prefix}*")
                for key in index_keys:
                    pipeline.delete(key)

                pipeline.execute()
        else:
            # Fallback to in-memory
            if pattern:
                keys_to_delete = [
                    k for k in self._memory_store.keys() if k.startswith(pattern)
                ]
                for key in keys_to_delete:
                    del self._memory_store[key]
                    count += 1
            else:
                count = len(self._memory_store)
                self._memory_store.clear()

        return count

    async def list_keys(
        self, pattern: Optional[str] = None, limit: int = 100
    ) -> List[str]:
        """List episode keys."""
        if not self._initialized:
            await self.initialize()

        if self._redis:
            if pattern:
                keys = self._redis.keys(f"{self._key_prefix}{pattern}*")
            else:
                keys = self._redis.keys(f"{self._key_prefix}*")

            # Remove prefix
            return [k.replace(self._key_prefix, "") for k in keys[:limit]]
        else:
            # Fallback to in-memory
            if pattern:
                return [k for k in self._memory_store.keys() if k.startswith(pattern)][
                    :limit
                ]
            else:
                return list(self._memory_store.keys())[:limit]

    # ------------------------------------------------------------------
    # Usage statistics
    # ------------------------------------------------------------------
    def get_usage_stats(self) -> Dict[str, float]:
        """Return cumulative token and cost usage for this episodic memory."""
        return {"tokens": self._token_total, "cost_usd": self._cost_total}

    async def get_conversation_history(
        self, participant: str, limit: int = 50
    ) -> List[MemoryEntry]:
        """Get conversation history for a specific participant."""
        return await self.search(
            query="", filters={"participant": participant}, limit=limit
        )

    async def get_recent_episodes(
        self, hours: int = 24, episode_type: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Get recent episodes within specified time window."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filters = {}
        if episode_type:
            filters["type"] = episode_type

        # Get episodes and filter by time
        episodes = await self.search("", filters=filters, limit=100)

        return [e for e in episodes if e.timestamp >= cutoff_time]

    async def analyze_patterns(
        self, participant: Optional[str] = None, episode_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze patterns in episodes."""
        filters = {}
        if participant:
            filters["participant"] = participant
        if episode_type:
            filters["type"] = episode_type

        episodes = await self.search("", filters=filters, limit=100)

        if not episodes:
            return {"total_episodes": 0, "patterns": {}, "insights": []}

        # Analyze patterns
        outcomes: Dict[str, int] = {}
        sentiments: Dict[str, int] = {}
        tags_freq: Dict[str, int] = {}
        hourly_distribution = [0] * 24

        for episode in episodes:
            # Count outcomes
            outcome = episode.metadata.get("outcome", "unknown")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

            # Count sentiments
            sentiment = episode.metadata.get("sentiment", "neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1

            # Count tags
            for tag in episode.metadata.get("tags", []):
                tags_freq[tag] = tags_freq.get(tag, 0) + 1

            # Hour distribution
            hour = episode.timestamp.hour
            hourly_distribution[hour] += 1

        # Generate insights
        insights = []

        # Success rate insight
        successful = outcomes.get("success", 0) + outcomes.get("sale", 0)
        total = len(episodes)
        if total > 0:
            success_rate = successful / total * 100
            insights.append(f"Success rate: {success_rate:.1f}%")

        # Sentiment insight
        positive = sentiments.get("positive", 0)
        if total > 0 and positive / total > 0.7:
            insights.append("High positive sentiment in interactions")

        # Peak hours
        peak_hour = hourly_distribution.index(max(hourly_distribution))
        if max(hourly_distribution) > total * 0.1:
            insights.append(f"Peak activity at {peak_hour}:00")

        return {
            "total_episodes": len(episodes),
            "patterns": {
                "outcomes": outcomes,
                "sentiments": sentiments,
                "top_tags": sorted(tags_freq.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ],
                "hourly_distribution": hourly_distribution,
            },
            "insights": insights,
        }
