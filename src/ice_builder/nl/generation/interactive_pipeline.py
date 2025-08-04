"""Interactive blueprint generation with preview and partial execution.

This module provides an interactive workflow where users can:
1. See a Mermaid diagram of the proposed plan
2. Approve or modify the plan
3. Execute the blueprint step by step
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ice_core.models.mcp import Blueprint, PartialBlueprint

from ..memory import DraftState, DraftStore, InMemoryDraftStore
from .atomic_workflow_principles import AtomicWorkflowPrinciples
from .multi_llm_orchestrator import MultiLLMOrchestrator


class PipelineStage(Enum):
    """Stages of the interactive pipeline."""
    INTENT = "intent_extraction"
    PLANNING = "planning"
    REVIEW = "plan_review"
    DECOMPOSITION = "decomposition"
    VALIDATION = "validation"
    DIAGRAM = "diagram_generation"
    APPROVAL = "user_approval"
    CODE_GEN = "code_generation"
    EXECUTION = "execution"


@dataclass
class PipelineState:
    """Current state of the interactive pipeline."""
    specification: str
    current_stage: PipelineStage
    intent_data: Optional[Dict[str, Any]] = None
    plan_text: Optional[str] = None
    nodes: Dict[str, Dict[str, Any]] | None = None
    mermaid_diagram: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    warnings: Optional[List[str]] = None
    questions: Optional[List[str]] = None
    
    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []
        if self.questions is None:
            self.questions = []
        if self.nodes is None:
            self.nodes = {}


class InteractiveBlueprintPipeline:
    """Interactive pipeline for blueprint generation with user feedback."""
    
    def __init__(self, specification: str, *, session_id: str = "dev", store: DraftStore | None = None) -> None:
        self._initialized = False
        """Initialize the interactive pipeline.
        
        Args:
            specification: Natural language specification.
        """
        self.orchestrator = MultiLLMOrchestrator(specification)
        self.principles = AtomicWorkflowPrinciples()
        self.session_id = session_id
        self.store: DraftStore = store or InMemoryDraftStore()
        # Initialise empty, actual loading happens in `initialize`.
        self.state = DraftState(prompt_history=[specification])

    async def _ensure_initialized(self) -> None:
        """Lazy-load DraftState from store on first usage."""
        if self._initialized:
            return
        loaded = await self.store.load(self.session_id)
        if loaded is not None:
            self.state = loaded
        self._initialized = True
    
    async def generate_preview(self) -> Tuple[str, List[str], List[str]]:
        """Generate a preview of the workflow with Mermaid diagram.
        
        Returns:
            Tuple of (mermaid_diagram, warnings, questions)
        """
        await self._ensure_initialized()
        # Run through planning stages
        await self._run_intent_extraction()
        await self._run_planning()
        await self._run_decomposition()
        
        # Generate early diagram for preview
        mermaid = await self._generate_preview_diagram()
        
        # Validate and generate warnings
        node_list = list(self.state.nodes.values())
        warnings = self.principles.validate_workflow_practicality(node_list)
        questions = self.principles.generate_clarifying_questions(node_list)
        
        self.state.mermaid_diagram = mermaid
        self.state.warnings = warnings
        self.state.questions = questions
        # Persist draft
        await self.store.save(self.session_id, self.state)  # type: ignore[arg-type]
        self.state.current_stage = PipelineStage.REVIEW
        
        return mermaid, warnings, questions
    
    async def revise_plan(self, user_feedback: str) -> Tuple[str, List[str], List[str]]:
        """Revise the plan based on user feedback.
        
        Args:
            user_feedback: User's revision instructions.
            
        Returns:
            Updated (mermaid_diagram, warnings, questions)
        """
        # Incorporate feedback into planning
        revision_prompt = f"""
Original request: {self.state.specification}

Current plan has these issues:
{chr(10).join(self.state.warnings)}

User feedback: {user_feedback}

Please revise the plan to address these concerns. Focus on:
- Using simple, atomic operations (tool/llm/code nodes)
- Avoiding unnecessary complexity (agents/swarms)
- Being specific about what each step does
"""
        
        # Re-run planning with feedback
        revised_plan = await self.orchestrator.providers["planning"].complete(revision_prompt)
        
        self.state.plan_text = revised_plan
        await self._run_decomposition()
        
        # Regenerate preview
        return await self.generate_preview()
    
    async def approve_and_generate(self) -> Blueprint:
        """Approve the plan and generate the full blueprint.
        
        Returns:
            Complete Blueprint ready for execution.
        """
        if self.state.current_stage != PipelineStage.REVIEW:
            raise ValueError("Must generate preview first")
        
        # Apply simplification rules
        simplified_nodes: Dict[str, Dict[str, Any]] = {}
        for node in self.state.nodes.values():
            simplified_type = self.principles.simplify_node_choice(
                node.get("description", ""),
                node.get("type", "")
            )
            node["type"] = simplified_type
            simplified_nodes[node["id"]] = node
        
        self.state.nodes = simplified_nodes
        await self.store.save(self.session_id, self.state)  # type: ignore[arg-type]
        self.state.current_stage = PipelineStage.APPROVAL
        
        # Generate full blueprint
        blueprint = await self._complete_generation()
        self.state.blueprint = blueprint
        await self.store.save(self.session_id, self.state)  # type: ignore[arg-type]
        self.state.current_stage = PipelineStage.EXECUTION
        
        return blueprint
    
    async def execute_partial(self, node_ids: List[str]) -> Dict[str, Any]:
        """Execute only specific nodes from the blueprint.
        
        Args:
            node_ids: IDs of nodes to execute.
            
        Returns:
            Execution results for the specified nodes.
        """
        if not self.state.blueprint:
            raise ValueError("Must generate blueprint first")
        
        # Create partial blueprint with only specified nodes
        partial_bp = PartialBlueprint(
            blueprint_id=f"{self.state.blueprint.blueprint_id}_partial",
            schema_version="1.1.0",
            nodes=[
                node for node in self.state.blueprint.nodes
                if node.id in node_ids
            ],
            metadata=self.state.blueprint.metadata,
        )
        
        # This would normally call the orchestrator
        # For now, return a placeholder
        return {
            "executed_nodes": node_ids,
            "status": "ready_for_execution",
            "partial_blueprint": partial_bp.model_dump(),
        }
    
    # Private helper methods
    
    async def _run_intent_extraction(self) -> None:
        """Run intent extraction stage."""
        self.state.intent_data = await self.orchestrator._extract_intent()
        self.state.current_stage = PipelineStage.PLANNING
    
    async def _run_planning(self) -> None:
        """Run planning stage."""
        if not self.state.intent_data:
            await self._run_intent_extraction()
        assert self.state.intent_data is not None
        self.state.plan_text = await self.orchestrator._create_plan(self.state.intent_data)
        self.state.current_stage = PipelineStage.DECOMPOSITION
    
    async def _run_decomposition(self) -> None:
        """Run decomposition stage."""
        if not self.state.plan_text:
            await self._run_planning()
        assert self.state.plan_text is not None
        new_nodes = await self.orchestrator._decompose_plan(self.state.plan_text)
        # ------------------------------------------------------------------
        # Honour locked / real nodes – never overwrite, only append
        # ------------------------------------------------------------------
        status_map = self.state.meta.get("status", {})
        preserved_ids = {nid for nid, s in status_map.items() if s in {"locked", "real"}}
        merged: Dict[str, Dict[str, Any]] = {}
        existing_by_id = self.state.nodes
        for node in new_nodes:
            if node["id"] in preserved_ids:
                merged[node["id"]] = existing_by_id[node["id"]]
            else:
                merged[node["id"]] = node
        # Preserve nodes missing from new draft
        for nid in preserved_ids:
            if nid not in merged and nid in existing_by_id:
                merged[nid] = existing_by_id[nid]
        self.state.nodes = merged
        self.state.current_stage = PipelineStage.VALIDATION
    
    async def _generate_preview_diagram(self) -> str:
        """Generate a Mermaid diagram for preview."""
        if not self.state.nodes:
            return "graph TD\n    A[No nodes defined]"
        
        # Generate simplified diagram
        lines = [
            "%%{init: {'theme': 'base'} }%%",
            "flowchart TD",
            "classDef DRAFT  stroke-dasharray: 4 4, fill:#EEEEEE, color:#555;",
            "classDef LOCKED fill:#B4C7FF,        color:#000;",
            "classDef REAL   fill:#90EE90,        color:#000;",
        ]
        
        # Add node definitions
        for i, node in enumerate(self.state.nodes.values()):
            node_id = node.get("id", f"node_{i}")
            node_type = node.get("type", "unknown")
            description = node.get("description", "")[:50]  # Truncate long descriptions
            
            # Style based on complexity
            # Determine status
            status_map = self.state.meta.get("status", {})
            raw_status = status_map.get(node_id)
            if raw_status is None:
                raw_status = "LOCKED" if node_id in self.state.locked_nodes else "DRAFT"
            status = raw_status.upper()
            # Shape selection (keep rectangle for now)
            lines.append(f'    {node_id}["{node_type}: {description}"]:::{status}')
        
        # Add dependencies
        for i, node in enumerate(self.state.nodes.values()):
            node_id = node["id"]
            for dep in node.get("dependencies", []):
                lines.append(f"    {dep} --> {node_id}")
        
        # Add legend
        lines.extend([
            "",
            "    subgraph Legend",
            '    Simple["Simple (tool/llm/code)"]',
            '    Medium["Medium (loop/parallel/human)"]', 
            '    Complex["Complex (agent/swarm)"]',
            "    end",
            "    style Simple fill:#90EE90",
            "    style Medium fill:#FFD700",
            "    style Complex fill:#FF6B6B",
        ])
        
        return "\n".join(lines)
    
    async def _complete_generation(self) -> Blueprint:
        """Complete the blueprint generation after approval."""
        # Generate final diagram
        final_diagram = await self.orchestrator._generate_diagram(list(self.state.nodes.values()))
        
        # Generate code implementations
        code_impls = await self.orchestrator._generate_code(list(self.state.nodes.values()))
        
        # Assemble blueprint
        blueprint = self.orchestrator._assemble_blueprint(
            list(self.state.nodes.values()),
            final_diagram,
            code_impls
        )
        
        return blueprint