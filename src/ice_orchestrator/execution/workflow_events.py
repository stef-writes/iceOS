"""Workflow execution events for real-time monitoring.

These events enable the canvas UI to show live execution progress.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum



class EventType(Enum):
    """Types of workflow events."""
    # Workflow lifecycle
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_PAUSED = "workflow.paused"
    WORKFLOW_RESUMED = "workflow.resumed"
    
    # Level execution
    LEVEL_STARTED = "level.started"
    LEVEL_COMPLETED = "level.completed"
    
    # Node execution
    NODE_QUEUED = "node.queued"
    NODE_STARTED = "node.started"
    NODE_PROGRESS = "node.progress"
    NODE_COMPLETED = "node.completed"
    NODE_FAILED = "node.failed"
    NODE_SKIPPED = "node.skipped"
    NODE_RETRYING = "node.retrying"
    
    # Resource tracking
    TOKEN_UPDATE = "resource.token_update"
    COST_UPDATE = "resource.cost_update"
    
    # Debugging
    CONTEXT_SNAPSHOT = "debug.context_snapshot"
    VALIDATION_ERROR = "debug.validation_error"
    
    # Canvas-specific
    SUGGESTION_AVAILABLE = "canvas.suggestion"
    PREVIEW_READY = "canvas.preview"


@dataclass
class WorkflowEvent(ABC):
    """Base class for all workflow events."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    workflow_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStarted(WorkflowEvent):
    """Emitted when workflow execution begins."""
    event_type: EventType = EventType.WORKFLOW_STARTED
    workflow_name: str = ""
    total_nodes: int = 0
    total_levels: int = 0
    estimated_duration_seconds: Optional[float] = None
    estimated_cost: Optional[float] = None


@dataclass 
class WorkflowCompleted(WorkflowEvent):
    """Emitted when workflow execution completes successfully."""
    event_type: EventType = EventType.WORKFLOW_COMPLETED
    duration_seconds: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    nodes_executed: int = 0
    nodes_skipped: int = 0


@dataclass
class NodeStarted(WorkflowEvent):
    """Emitted when a node begins execution."""
    event_type: EventType = EventType.NODE_STARTED
    node_id: str = ""
    node_type: str = ""
    node_name: Optional[str] = None
    level: int = 0
    dependencies: List[str] = field(default_factory=list)
    input_size_bytes: Optional[int] = None


@dataclass
class NodeProgress(WorkflowEvent):
    """Emitted to report node execution progress."""
    event_type: EventType = EventType.NODE_PROGRESS
    node_id: str = ""
    progress_percent: float = 0.0
    message: Optional[str] = None
    tokens_used: Optional[int] = None


@dataclass
class NodeCompleted(WorkflowEvent):
    """Emitted when a node completes successfully."""
    event_type: EventType = EventType.NODE_COMPLETED
    node_id: str = ""
    duration_seconds: float = 0.0
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    output_preview: Optional[Dict[str, Any]] = None
    cache_hit: bool = False


@dataclass
class NodeFailed(WorkflowEvent):
    """Emitted when a node fails."""
    event_type: EventType = EventType.NODE_FAILED
    node_id: str = ""
    error_type: str = ""
    error_message: str = ""
    retry_attempt: int = 0
    will_retry: bool = False
    stack_trace: Optional[str] = None


@dataclass
class CanvasSuggestion(WorkflowEvent):
    """Emitted when AI has suggestions for the canvas."""
    event_type: EventType = EventType.SUGGESTION_AVAILABLE
    context_node_id: Optional[str] = None
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    reason: Optional[str] = None


class WorkflowEventHandler:
    """Manages workflow event subscribers."""
    
    def __init__(self):
        self._handlers: Dict[EventType, List[Any]] = {}
        self._global_handlers: List[Any] = []
        
    def subscribe(self, event_type: EventType, handler: Any) -> None:
        """Subscribe to specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
    def subscribe_all(self, handler: Any) -> None:
        """Subscribe to all events."""
        self._global_handlers.append(handler)
        
    async def emit(self, event: WorkflowEvent) -> None:
        """Emit event to all subscribers."""
        # Type-specific handlers
        for handler in self._handlers.get(event.event_type, []):
            await self._safe_call_handler(handler, event)
            
        # Global handlers
        for handler in self._global_handlers:
            await self._safe_call_handler(handler, event)
            
    async def _safe_call_handler(self, handler: Any, event: WorkflowEvent) -> None:
        """Safely call handler, catching exceptions."""
        try:
            result = handler(event)
            if hasattr(result, '__await__'):
                await result
        except Exception as e:
            # Log but don't fail workflow on handler errors
            import structlog
            logger = structlog.get_logger(__name__)
            logger.error(
                "Event handler error",
                event_type=event.event_type.value,
                error=str(e),
                handler=handler.__name__ if hasattr(handler, '__name__') else str(handler)
            ) 