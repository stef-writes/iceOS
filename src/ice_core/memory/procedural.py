"""Procedural memory for storing action patterns and strategies."""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ice_core.models.enums import MemoryGuarantee

from .base import BaseMemory, MemoryConfig, MemoryEntry


class ProceduralMemory(BaseMemory):
    """Memory for storing successful action sequences and strategies.

    This stores reusable patterns that agents can apply, including:
    - Successful negotiation strategies
    - Common response templates
    - Action sequences that led to sales
    - Problem-solving patterns
    """

    # ------------------------------------------------------------------
    # MemoryGuarantee interface
    # ------------------------------------------------------------------
    def guarantees(self) -> set[MemoryGuarantee]:  # noqa: D401
        return {MemoryGuarantee.DURABLE}

    def __init__(self, config: MemoryConfig):
        """Initialize procedural memory."""
        super().__init__(config)
        self._procedures: Dict[str, MemoryEntry] = {}

        # 🚀 NESTED STRUCTURE: Categories -> Items -> Metrics
        self._success_metrics: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._usage_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._category_index: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._context_index: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

    async def initialize(self) -> None:
        """Initialize procedural memory backend."""
        if self._initialized:
            return

        self._initialized = True  # Set this FIRST to prevent recursion

    # 🚀 NEW: High-performance nested query methods
    def get_procedures_by_category(
        self, category: str, procedure_type: Optional[str] = None
    ) -> List[str]:
        """Get procedures by category and type - MUCH faster than scanning all!"""
        if procedure_type:
            return self._category_index.get(category, {}).get(procedure_type, [])
        else:
            result = []
            for proc_type_dict in self._category_index.get(category, {}).values():
                result.extend(proc_type_dict)
            return result

    def get_procedures_by_context(
        self, domain: str, context: Optional[str] = None
    ) -> List[str]:
        """Get procedures by domain and context - targeted querying!"""
        if context:
            return self._context_index.get(domain, {}).get(context, [])
        else:
            result = []
            for context_dict in self._context_index.get(domain, {}).values():
                result.extend(context_dict)
            return result

    def get_success_metrics_for_domain(self, domain: str) -> Dict[str, List[float]]:
        """Get all success metrics for domain - perfect for analytics!"""
        return dict(self._success_metrics.get(domain, {}))

    def get_usage_stats_for_domain(self, domain: str) -> Dict[str, int]:
        """Get usage statistics for domain - great for monitoring!"""
        return dict(self._usage_counts.get(domain, {}))

    def list_categories(self) -> List[str]:
        """List all procedure categories - organizational view!"""
        return list(self._category_index.keys())

    def list_domains(self) -> List[str]:
        """List all domains - high-level overview!"""
        return list(self._context_index.keys())

        # In production, would load from file or database
        # Default procedures will be loaded lazily in initialize()

    async def _load_default_procedures(self) -> None:
        """Load default procedures for marketplace selling."""
        # Default negotiation strategies
        await self.store(
            key="negotiation_standard",
            content={
                "name": "Standard Negotiation",
                "steps": [
                    {
                        "action": "acknowledge_offer",
                        "template": "I appreciate your offer!",
                    },
                    {"action": "evaluate_offer", "condition": "offer >= price * 0.8"},
                    {
                        "action": "counter_offer",
                        "formula": "price * 0.9",
                        "template": "I could do ${counter} for you.",
                    },
                    {
                        "action": "create_urgency",
                        "template": "I have other interested buyers, so let me know soon!",
                    },
                ],
                "applicable_when": {
                    "offer_range": [0.7, 0.9],
                    "buyer_engagement": "high",
                    "item_demand": "medium",
                },
            },
            metadata={
                "category": "negotiation",
                "success_rate": 0.65,
                "contexts": ["price_inquiry", "offer_received"],
            },
        )

        # Response templates
        await self.store(
            key="response_availability_positive",
            content={
                "name": "Positive Availability Response",
                "template": "Yes! This {item_name} is still available and in {condition} condition. Would you like to see it?",
                "variables": ["item_name", "condition"],
                "sentiment": "positive",
                "follow_up": "ask_viewing_interest",
            },
            metadata={
                "category": "response_template",
                "success_rate": 0.8,
                "contexts": ["availability_check", "initial_inquiry"],
            },
        )

        # Sales closing sequence
        await self.store(
            key="closing_sequence_standard",
            content={
                "name": "Standard Sales Closing",
                "steps": [
                    {
                        "action": "confirm_interest",
                        "template": "Great choice! You're going to love this {item}.",
                    },
                    {
                        "action": "arrange_pickup",
                        "template": "When would work best for pickup? I'm available {availability}.",
                    },
                    {"action": "share_location", "condition": "pickup_time_agreed"},
                    {"action": "send_reminder", "timing": "1_hour_before"},
                ],
                "success_indicators": ["buyer_confirms", "pickup_scheduled"],
            },
            metadata={
                "category": "sales_closing",
                "success_rate": 0.85,
                "contexts": ["purchase_intent", "deal_agreed"],
            },
        )

    async def store(
        self, key: str, content: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a procedure or action pattern."""
        if not self._initialized:
            await self.initialize()

        metadata = metadata or {}

        # Validate procedure format
        if not isinstance(content, dict):
            raise ValueError("Procedure content must be a dictionary")

        if "name" not in content:
            raise ValueError("Procedure must have a name")

        # Create memory entry
        entry = MemoryEntry(
            key=key, content=content, metadata=metadata, timestamp=datetime.now()
        )

        # Add procedural-specific metadata
        entry.metadata.update(
            {
                "category": metadata.get("category", "general"),
                "success_rate": metadata.get("success_rate", 0.5),
                "usage_count": 0,
                "last_used": None,
                "contexts": metadata.get("contexts", []),
                "prerequisites": metadata.get("prerequisites", []),
                "outcomes": metadata.get("outcomes", []),
            }
        )

        # Store procedure
        self._procedures[key] = entry

        # Index by category and procedure type for better organization
        category = entry.metadata.get("category", "general")
        procedure_type = entry.metadata.get("type", "generic")
        self._category_index[category][procedure_type].append(key)

        # Index by context with nesting for better performance
        domain = entry.metadata.get("domain", "general")
        for context in entry.metadata.get("contexts", []):
            self._context_index[domain][context].append(key)

    async def retrieve(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve a specific procedure."""
        if not self._initialized:
            await self.initialize()

        return self._procedures.get(key)

    async def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """Search procedures by description or outcome."""
        if not self._initialized:
            await self.initialize()

        filters = filters or {}
        matching_procedures = []

        for key, entry in self._procedures.items():
            # Apply filters
            if not self._match_filters(entry, filters):
                continue

            # Search in content
            content_str = json.dumps(entry.content).lower()
            if query.lower() in content_str:
                matching_procedures.append(entry)

        # Sort by success rate and usage
        matching_procedures.sort(
            key=lambda e: (
                e.metadata.get("success_rate", 0) * 0.7
                + min(e.metadata.get("usage_count", 0) / 100, 0.3)
            ),
            reverse=True,
        )

        return matching_procedures[:limit]

    def _match_filters(self, entry: MemoryEntry, filters: Dict[str, Any]) -> bool:
        """Check if procedure matches filters."""
        if not filters:
            return True

        metadata = entry.metadata

        if "category" in filters and metadata.get("category") != filters["category"]:
            return False

        if "min_success_rate" in filters:
            if metadata.get("success_rate", 0) < filters["min_success_rate"]:
                return False

        if "context" in filters:
            contexts = metadata.get("contexts", [])
            if filters["context"] not in contexts:
                return False

        if "has_prerequisites" in filters:
            has_prereq = bool(metadata.get("prerequisites"))
            if has_prereq != filters["has_prerequisites"]:
                return False

        return True

    async def delete(self, key: str) -> bool:
        """Delete a procedure."""
        if not self._initialized:
            await self.initialize()

        if key not in self._procedures:
            return False

        entry = self._procedures[key]

        # Remove from nested category index
        category = entry.metadata.get("category", "general")
        procedure_type = entry.metadata.get("type", "generic")
        if (
            category in self._category_index
            and procedure_type in self._category_index[category]
        ):
            if key in self._category_index[category][procedure_type]:
                self._category_index[category][procedure_type].remove(key)
                if not self._category_index[category][procedure_type]:
                    del self._category_index[category][procedure_type]
                    if not self._category_index[category]:
                        del self._category_index[category]

        # Remove from nested context index
        domain = entry.metadata.get("domain", "general")
        for context in entry.metadata.get("contexts", []):
            if domain in self._context_index and context in self._context_index[domain]:
                if key in self._context_index[domain][context]:
                    self._context_index[domain][context].remove(key)
                    if not self._context_index[domain][context]:
                        del self._context_index[domain][context]
                        if not self._context_index[domain]:
                            del self._context_index[domain]

        # Remove procedure
        del self._procedures[key]

        # Clean up nested metrics
        for domain_metrics in self._success_metrics.values():
            if key in domain_metrics:
                del domain_metrics[key]
        if key in self._usage_counts:
            del self._usage_counts[key]

        return True

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear procedures matching pattern."""
        if not self._initialized:
            await self.initialize()

        if pattern:
            keys_to_delete = [
                k for k in self._procedures.keys() if k.startswith(pattern)
            ]
        else:
            keys_to_delete = list(self._procedures.keys())

        count = 0
        for key in keys_to_delete:
            if await self.delete(key):
                count += 1

        return count

    async def list_keys(
        self, pattern: Optional[str] = None, limit: int = 100
    ) -> List[str]:
        """List procedure keys."""
        if not self._initialized:
            await self.initialize()

        if pattern:
            keys = [k for k in self._procedures.keys() if k.startswith(pattern)]
        else:
            keys = list(self._procedures.keys())

        return keys[:limit]

    async def find_applicable_procedures(
        self, context: Dict[str, Any], category: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Find procedures applicable to current context."""
        if not self._initialized:
            await self.initialize()

        applicable = []

        # Get procedures by category if specified
        if category:
            category_data = self._category_index.get(category, {})
            category_procedure_keys: List[str] = []
            for proc_type_dict in category_data.values():
                category_procedure_keys.extend(proc_type_dict)
            procedure_keys = category_procedure_keys
        else:
            all_procedure_keys: List[str] = list(self._procedures.keys())
            procedure_keys = all_procedure_keys

        for key in procedure_keys:
            entry = self._procedures.get(key)
            if not entry:
                continue

            # Check if procedure applies to this context
            if self._is_applicable(entry, context):
                applicable.append(entry)

        # Sort by success rate
        applicable.sort(key=lambda e: e.metadata.get("success_rate", 0), reverse=True)

        return applicable

    def _is_applicable(self, procedure: MemoryEntry, context: Dict[str, Any]) -> bool:
        """Check if procedure is applicable to context."""
        content = procedure.content
        metadata = procedure.metadata

        # Check context match
        proc_contexts = metadata.get("contexts", [])
        current_context = context.get("type", "")

        if proc_contexts and current_context not in proc_contexts:
            return False

        # Check prerequisites
        prerequisites = metadata.get("prerequisites", [])
        for prereq in prerequisites:
            if not context.get(prereq):
                return False

        # Check applicable conditions in content
        if "applicable_when" in content:
            conditions = content["applicable_when"]

            # Check numeric ranges
            for field, range_val in conditions.items():
                if isinstance(range_val, list) and len(range_val) == 2:
                    context_val = context.get(field)
                    if context_val is not None:
                        if not (range_val[0] <= context_val <= range_val[1]):
                            return False
                else:
                    # Direct value match
                    if context.get(field) != range_val:
                        return False

        return True

    async def record_execution(
        self, procedure_key: str, outcome: Dict[str, Any]
    ) -> None:
        """Record the execution of a procedure and its outcome."""
        if not self._initialized:
            await self.initialize()

        entry = self._procedures.get(procedure_key)
        if not entry:
            return

        # Update usage count with nested structure
        domain = entry.metadata.get("domain", "general")
        self._usage_counts[domain][procedure_key] += 1
        entry.metadata["usage_count"] = self._usage_counts[domain][procedure_key]
        entry.metadata["last_used"] = datetime.now().isoformat()

        # Record success metric in nested structure
        success_score = outcome.get("success_score", 0.5)
        self._success_metrics[domain][procedure_key].append(success_score)

        # Update success rate (weighted average)
        metrics = self._success_metrics[domain][procedure_key]
        if len(metrics) > 1:
            # Weight recent executions more heavily
            weights = [0.5**i for i in range(len(metrics) - 1, -1, -1)]
            weighted_sum = sum(m * w for m, w in zip(metrics, weights))
            weight_total = sum(weights)
            new_success_rate = weighted_sum / weight_total
            entry.metadata["success_rate"] = new_success_rate

        # Learn from outcome
        if "learned_adjustments" in outcome:
            await self._apply_learned_adjustments(
                procedure_key, outcome["learned_adjustments"]
            )

    async def _apply_learned_adjustments(
        self, procedure_key: str, adjustments: Dict[str, Any]
    ) -> None:
        """Apply learned adjustments to improve procedure."""
        entry = self._procedures.get(procedure_key)
        if not entry:
            return

        content = entry.content

        # Apply adjustments based on type
        if "template_improvements" in adjustments:
            for step_idx, improvement in adjustments["template_improvements"].items():
                if "steps" in content and int(step_idx) < len(content["steps"]):
                    content["steps"][int(step_idx)]["template"] = improvement

        if "condition_adjustments" in adjustments:
            if "applicable_when" not in content:
                content["applicable_when"] = {}
            content["applicable_when"].update(adjustments["condition_adjustments"])

        # Mark as modified
        entry.metadata["last_modified"] = datetime.now().isoformat()
        entry.metadata["modification_count"] = (
            entry.metadata.get("modification_count", 0) + 1
        )

    async def get_best_procedures(
        self, category: str, min_success_rate: float = 0.6
    ) -> List[MemoryEntry]:
        """Get best performing procedures in a category."""
        filters = {"category": category, "min_success_rate": min_success_rate}

        procedures = await self.search("", filters=filters, limit=10)

        # Additional filtering for minimum usage
        experienced_procedures = [
            p for p in procedures if p.metadata.get("usage_count", 0) >= 5
        ]

        return (
            experienced_procedures or procedures[:3]
        )  # Return top 3 if none are experienced

    async def create_composite_procedure(
        self, component_keys: List[str], composite_key: str, name: str
    ) -> bool:
        """Create a composite procedure from multiple components."""
        if not self._initialized:
            await self.initialize()

        components = []
        for key in component_keys:
            entry = self._procedures.get(key)
            if entry:
                components.append(entry)

        if not components:
            return False

        # Build composite procedure
        composite_steps = []
        all_contexts = set()
        all_prerequisites = set()

        for comp in components:
            content = comp.content

            # Add steps
            if "steps" in content:
                composite_steps.extend(content["steps"])
            elif "template" in content:
                # Single template procedure
                composite_steps.append(
                    {
                        "action": "use_template",
                        "template": content["template"],
                        "source": comp.key,
                    }
                )

            # Collect contexts and prerequisites
            all_contexts.update(comp.metadata.get("contexts", []))
            all_prerequisites.update(comp.metadata.get("prerequisites", []))

        # Create composite
        await self.store(
            key=composite_key,
            content={
                "name": name,
                "type": "composite",
                "components": component_keys,
                "steps": composite_steps,
            },
            metadata={
                "category": "composite",
                "contexts": list(all_contexts),
                "prerequisites": list(all_prerequisites),
                "success_rate": 0.5,  # Start neutral
            },
        )

        return True

    async def export_successful_procedures(
        self, min_success_rate: float = 0.7, min_usage: int = 10
    ) -> Dict[str, Any]:
        """Export successful procedures for sharing or backup."""
        if not self._initialized:
            await self.initialize()

        successful_procedures = {}

        for key, entry in self._procedures.items():
            metadata = entry.metadata

            if (
                metadata.get("success_rate", 0) >= min_success_rate
                and metadata.get("usage_count", 0) >= min_usage
            ):
                successful_procedures[key] = {
                    "content": entry.content,
                    "metadata": {
                        "category": metadata.get("category"),
                        "success_rate": metadata.get("success_rate"),
                        "usage_count": metadata.get("usage_count"),
                        "contexts": metadata.get("contexts", []),
                    },
                }

        return {
            "procedures": successful_procedures,
            "export_date": datetime.now().isoformat(),
            "criteria": {"min_success_rate": min_success_rate, "min_usage": min_usage},
        }
