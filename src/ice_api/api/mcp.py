"""MCP (Model Context Protocol) API implementation.

WHY THIS MODULE EXISTS:
- This is the "Compiler Tier" of the 3-tier architecture
- Validates blueprints before they reach the runtime
- Enables incremental construction for canvas UI
- Provides optimization and governance before execution

ARCHITECTURAL ROLE:
- Receives: Blueprint specifications (from Frosty/UI)
- Validates: Schema, permissions, budget limits
- Optimizes: Suggests better models, caching opportunities
- Returns: Validated blueprints ready for runtime

KEY FEATURES:
1. Partial blueprint support for incremental canvas building
2. Multi-tenancy with isolated contexts
3. Cost estimation before execution
4. Governance rules (PII, budget caps)

This layer exists to separate "design time" from "runtime" - allowing
the canvas UI to build workflows progressively without executing them.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import uuid
from typing import Any, Dict, List, Literal, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

# Try to import EventSourceResponse, fallback if not available
try:
    from sse_starlette import EventSourceResponse
except ImportError:
    EventSourceResponse = Any  # type: ignore

logger = logging.getLogger(__name__)

import os

# Redis helper
from ice_api.redis_client import get_redis
from ice_core.models import INode, NodeType
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.models.mcp import (
    AgentDefinition,
    Blueprint,
    BlueprintAck,
    ComponentDefinition,
    ComponentValidationResult,
    NodeSpec,
    PartialBlueprint,
    PartialBlueprintUpdate,
    PartialNodeSpec,
    RunAck,
    RunRequest,
    RunResult,
)
from ice_core.registry import global_agent_registry, registry
from ice_core.services.contracts import IWorkflowService

# Import execution guard to allow orchestrator runtime during MCP execution

# Fetch service lazily to avoid bootstrap order problems --------------------


def _get_workflow_service() -> IWorkflowService:
    """Return workflow service instance.

    Uses the orchestrator implementation directly; this keeps API decoupled
    from orchestrator imports at module import time while avoiding the global
    ServiceLocator.
    """
    # Defer import to runtime initialization step via subprocess CLI
    # to avoid app→orchestrator hard dependency at import time.
    # When orchestrator is installed, we instantiate its WorkflowService.
    try:
        from importlib import import_module

        wf_mod = import_module("ice_orchestrator.services.workflow_service")
        return cast(IWorkflowService, getattr(wf_mod, "WorkflowService")())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Orchestrator unavailable: {exc}")


router = APIRouter(tags=["mcp"])
from ice_api.dependencies import rate_limit
from ice_api.security import require_auth

# ---------------------------------------------------------------------------
# In-memory stores – good enough for MVP; swap with DB / Redis later --------
# ---------------------------------------------------------------------------

# In-memory fallback stores (only for unit-tests) ---------------------------
_RUNS: Dict[str, RunResult] = {}
_EVENTS: Dict[str, List[str]] = {}

# Redis keys helpers --------------------------------------------------------


def _bp_key(bp_id: str) -> str:
    return f"bp:{bp_id}"


def _stream_key(run_id: str) -> str:
    return f"stream:{run_id}"


def _partial_bp_key(bp_id: str) -> str:
    return f"partial_bp:{bp_id}"


# ---------------------------------------------------------------------------
# Routes --------------------------------------------------------------------
# ---------------------------------------------------------------------------


@router.post(
    "/blueprints", response_model=BlueprintAck, status_code=status.HTTP_201_CREATED
)
async def create_blueprint(bp: Blueprint) -> BlueprintAck:
    """Register (or upsert) a *Blueprint*."""

    # Validate blueprint comprehensively ---------------------------------
    from ice_core.validation.schema_validator import validate_blueprint

    validation_context: Dict[str, list[str]] = {"validation_errors": [], "warnings": []}

    try:
        # Design-time (schema version, dependency graph, tool parameter match)
        await validate_blueprint(bp)  # Raises on failure

        # Runtime-convert to ensure NodeSpecs are materially valid
        bp.validate_runtime()
        from ice_core.utils.node_conversion import convert_node_specs

        cfgs = convert_node_specs(bp.nodes)
        for cfg in cfgs:
            if hasattr(cfg, "runtime_validate"):
                cfg.runtime_validate()  # type: ignore[attr-defined]
    except Exception as exc:
        validation_context["validation_errors"].append(str(exc))
        raise HTTPException(400, detail=str(exc))

    # TODO: Re-enable blueprint visualization when toolkit is implemented
    visualization_data = None
    # try:
    #     from ice_tools.builtin.blueprint_visualization_tool import (
    #         BlueprintVisualizationTool,
    #     )
    #     from ice_tools.builtin.config import is_tool_enabled
    #
    #     if is_tool_enabled("blueprint_visualization"):
    #         viz_tool = BlueprintVisualizationTool()
    #         visualization_result = await viz_tool.execute(
    #             blueprint=bp,
    #             diagram_types=["dependency_graph", "workflow_flowchart", "validation_diagram"],
    #             validation_context=validation_context
    #         )
    #
    #         if visualization_result.get("status") == "success":
    #             visualization_data = visualization_result
    #             logger.info("Generated blueprint visualization for %s", bp.blueprint_id)
    # except Exception as ve:
    #     # Don't fail blueprint creation if visualization fails
    #     logger.warning("Failed to generate blueprint visualization: %s", str(ve))
    #     validation_context["warnings"].append(f"Visualization generation failed: {str(ve)}")

    # Enforce content-addressable Blueprint IDs (sha256 over normalized JSON)
    import hashlib

    normalized = bp.model_dump_json()
    content_id = f"bp_{hashlib.sha256(normalized.encode()).hexdigest()[:12]}"

    # Overwrite provided id with content-derived id for immutability
    bp.blueprint_id = content_id

    redis = get_redis()
    blueprint_data = {"json": bp.model_dump_json()}

    # Store visualization data if available
    if visualization_data:
        blueprint_data["visualization"] = json.dumps(visualization_data)

    await redis.hset(_bp_key(bp.blueprint_id), mapping=blueprint_data)
    return BlueprintAck(blueprint_id=bp.blueprint_id, status="accepted")


@router.get("/blueprints/{blueprint_id}")
async def get_blueprint(blueprint_id: str) -> Dict[str, Any]:
    """Retrieve a registered blueprint by ID."""
    redis = get_redis()
    blueprint_data = await redis.hgetall(_bp_key(blueprint_id))  # type: ignore[misc]

    if not blueprint_data or "json" not in blueprint_data:
        raise HTTPException(404, detail=f"Blueprint {blueprint_id} not found")

    blueprint = Blueprint.model_validate_json(blueprint_data["json"])
    result = blueprint.model_dump()

    # Include visualization data if available
    if "visualization" in blueprint_data:
        try:
            result["visualization"] = json.loads(blueprint_data["visualization"])
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Failed to parse visualization data for blueprint %s", blueprint_id
            )

    # Add computed content hash for observability and verification
    import hashlib

    normalized = blueprint.model_dump_json()
    result["content_id"] = f"bp_{hashlib.sha256(normalized.encode()).hexdigest()[:12]}"

    return result


@router.get("/blueprints/{blueprint_id}/visualization")
async def get_blueprint_visualization(blueprint_id: str) -> Dict[str, Any]:
    """Get visualization data for a blueprint."""
    redis = get_redis()
    blueprint_data = await redis.hgetall(_bp_key(blueprint_id))  # type: ignore[misc]

    if not blueprint_data or "json" not in blueprint_data:
        raise HTTPException(404, detail=f"Blueprint {blueprint_id} not found")

    # If visualization data exists, return it
    if "visualization" in blueprint_data:
        try:
            return cast(Dict[str, Any], json.loads(blueprint_data["visualization"]))
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Failed to parse visualization data for blueprint %s", blueprint_id
            )
            raise HTTPException(500, detail="Invalid visualization data")

    # TODO: Re-enable visualization on-demand when toolkit is implemented
    raise HTTPException(501, detail="Blueprint visualization not yet implemented")

    # try:
    #     blueprint = Blueprint.model_validate_json(blueprint_data["json"])
    #
    #     from ice_tools.builtin.blueprint_visualization_tool import (
    #         BlueprintVisualizationTool,
    #     )
    #     from ice_tools.builtin.config import is_tool_enabled
    #
    #     if not is_tool_enabled("blueprint_visualization"):
    #         raise HTTPException(503, detail="Blueprint visualization tool is not enabled")
    #
    #     viz_tool = BlueprintVisualizationTool()
    #     visualization_result = await viz_tool.execute(
    #         blueprint=blueprint,
    #         diagram_types=["dependency_graph", "workflow_flowchart", "config_overview", "validation_diagram"]
    #     )
    #
    #     if visualization_result.get("status") == "success":
    #         # Cache the result for future requests
    #         await redis.hset(_bp_key(blueprint_id), "visualization", json.dumps(visualization_result))
    #         return visualization_result
    #     else:
    #         raise HTTPException(500, detail=f"Visualization generation failed: {visualization_result.get('error', 'Unknown error')}")
    #
    # except ImportError:
    #     raise HTTPException(503, detail="Blueprint visualization tool is not available")
    # except Exception as e:
    #     logger.error("Failed to generate visualization for blueprint %s: %s", blueprint_id, str(e))
    #     raise HTTPException(500, detail=f"Visualization generation failed: {str(e)}")


# ---------------------------------------------------------------------------
# Partial Blueprint Routes (Incremental Construction) -----------------------
# ---------------------------------------------------------------------------


@router.post(
    "/blueprints/partial",
    response_model=PartialBlueprint,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def create_partial_blueprint(
    request: Request,
    initial_node: Optional[PartialNodeSpec] = None,
) -> PartialBlueprint:
    """Create a new partial blueprint for incremental construction."""
    partial = PartialBlueprint()

    if initial_node:
        partial.add_node(initial_node)

    redis = get_redis()
    # Persist with optimistic version-lock stored alongside JSON
    import hashlib
    import json as _json

    lock = hashlib.sha256(
        _json.dumps(
            partial.model_dump(mode="json", exclude_none=True), sort_keys=True
        ).encode()
    ).hexdigest()
    await redis.hset(
        _partial_bp_key(partial.blueprint_id),
        mapping={"json": partial.model_dump_json(), "lock": lock},
    )

    return partial


@router.put(
    "/blueprints/partial/{blueprint_id}",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def update_partial_blueprint(
    request: Request, blueprint_id: str, update: PartialBlueprintUpdate
) -> PartialBlueprint:
    """Update a partial blueprint - add/remove/modify nodes."""
    redis = get_redis()
    raw_json = await redis.hget(_partial_bp_key(blueprint_id), "json")  # type: ignore[misc]
    server_lock = await redis.hget(_partial_bp_key(blueprint_id), "lock")  # type: ignore[misc]

    if not raw_json:
        raise HTTPException(404, f"Partial blueprint {blueprint_id} not found")

    partial = PartialBlueprint.model_validate_json(raw_json)

    # Optimistic lock enforcement using X-Version-Lock header
    client_lock = request.headers.get("X-Version-Lock")
    if client_lock is None:
        raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")
    if not server_lock or client_lock != server_lock:
        raise HTTPException(
            status_code=409, detail="Partial blueprint version conflict"
        )

    if update.action == "add_node" and update.node:
        partial.add_node(update.node)
    elif update.action == "remove_node" and update.node_id:
        partial.nodes = [n for n in partial.nodes if n.id != update.node_id]
        partial._validate_incremental()
    elif update.action == "update_node" and update.node_id and update.updates:
        for i, node in enumerate(partial.nodes):
            if node.id == update.node_id:
                # Update node fields
                node_dict = node.model_dump()
                node_dict.update(update.updates)
                partial.nodes[i] = PartialNodeSpec(**node_dict)
                break
        partial._validate_incremental()
    elif update.action == "suggest":
        # Just trigger revalidation to get fresh suggestions
        partial._validate_incremental()

    # Save updated state
    # Save updated state with new version lock
    import hashlib
    import json as _json

    new_lock = hashlib.sha256(
        _json.dumps(
            partial.model_dump(mode="json", exclude_none=True), sort_keys=True
        ).encode()
    ).hexdigest()
    await redis.hset(
        _partial_bp_key(partial.blueprint_id),
        mapping={"json": partial.model_dump_json(), "lock": new_lock},
    )

    # Expose new lock via header for client to use
    # (FastAPI response object not passed here; clients should GET session to fetch lock)

    return partial


@router.post(
    "/blueprints/partial/{blueprint_id}/finalize",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def finalize_partial_blueprint(
    request: Request, blueprint_id: str
) -> BlueprintAck:
    """Convert partial blueprint to executable blueprint."""
    redis = get_redis()
    raw_json = await redis.hget(_partial_bp_key(blueprint_id), "json")  # type: ignore[misc]
    server_lock = await redis.hget(_partial_bp_key(blueprint_id), "lock")  # type: ignore[misc]

    if not raw_json:
        raise HTTPException(404, f"Partial blueprint {blueprint_id} not found")

    partial = PartialBlueprint.model_validate_json(raw_json)

    # Require lock header to avoid finalizing stale state
    client_lock = request.headers.get("X-Version-Lock")
    if client_lock is None:
        raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")
    if not server_lock or client_lock != server_lock:
        raise HTTPException(
            status_code=409, detail="Partial blueprint version conflict"
        )

    # If the partial has no nodes, fail fast with a clear message before preflight
    if not partial.nodes:
        raise HTTPException(400, "Partial blueprint has no nodes to finalize")

    try:
        blueprint = partial.to_blueprint()
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Governance preflight: schema + safety + budget estimate
    try:
        from ice_core.validation.schema_validator import validate_blueprint

        await validate_blueprint(blueprint)
    except Exception as ve:
        raise HTTPException(400, f"Blueprint schema validation failed: {ve}")

    # Budget estimate (best-effort)
    try:
        from importlib import import_module

        from ice_core.utils.node_conversion import convert_node_specs

        WorkflowCostEstimator = getattr(
            import_module("ice_orchestrator.execution.cost_estimator"),
            "WorkflowCostEstimator",
        )

        node_cfgs = convert_node_specs(blueprint.nodes)
        estimator = WorkflowCostEstimator()
        est = estimator.estimate_workflow_cost(node_cfgs)

        from importlib import import_module

        runtime_config = getattr(
            import_module("ice_orchestrator.config"), "runtime_config"
        )

        if (
            runtime_config.org_budget_usd is not None
            and est.total_avg_cost > runtime_config.org_budget_usd
        ):
            raise HTTPException(
                402,  # Payment Required (budget exceeded)
                detail=f"Estimated cost ${est.total_avg_cost:.2f} exceeds budget ${runtime_config.org_budget_usd:.2f}",
            )
    except HTTPException:
        raise
    except Exception:
        # Ignore estimator errors – preflight is best-effort
        pass

    # Save as regular blueprint with content-addressable id
    import hashlib

    normalized = blueprint.model_dump_json()
    content_id = f"bp_{hashlib.sha256(normalized.encode()).hexdigest()[:12]}"
    blueprint.blueprint_id = content_id

    await redis.hset(
        _bp_key(blueprint.blueprint_id), mapping={"json": blueprint.model_dump_json()}
    )

    # Clean up partial
    await redis.hdel(_partial_bp_key(blueprint_id), "json")

    return BlueprintAck(blueprint_id=blueprint.blueprint_id, status="accepted")


@router.get(
    "/blueprints/partial/{blueprint_id}",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def get_partial_blueprint(
    blueprint_id: str, response: Response
) -> Dict[str, Any]:  # noqa: D401
    """Return stored PartialBlueprint JSON and expose current lock in header."""
    redis = get_redis()
    raw_json = await redis.hget(_partial_bp_key(blueprint_id), "json")  # type: ignore[misc]
    if not raw_json:
        raise HTTPException(404, f"Partial blueprint {blueprint_id} not found")
    lock = await redis.hget(_partial_bp_key(blueprint_id), "lock")  # type: ignore[misc]
    if lock:
        response.headers["X-Version-Lock"] = str(lock)
    pb = PartialBlueprint.model_validate_json(raw_json)
    return pb.model_dump()


# ---------------------------------------------------------------------------
# Suggestions (deterministic MVP) -------------------------------------------
# ---------------------------------------------------------------------------


class SuggestRequest(BaseModel):
    """Request for suggestions for next nodes.

    Args:
        top_k: Maximum number of suggestions to return
        allowed_types: Optional filter of node types to include
        commit: If true, persist summary suggestions and roll lock (requires X-Version-Lock)
    """

    top_k: int = Field(default=5, ge=1, le=20)
    allowed_types: Optional[List[str]] = None
    commit: bool = False


class Suggestion(BaseModel):
    type: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)
    template: Optional[Dict[str, Any]] = None


class SuggestResponse(BaseModel):
    suggestions: List[Suggestion]
    context: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Component Lifecycle (Scaffold, Register, CRUD, List) -----------------------
# ---------------------------------------------------------------------------


class ComponentScaffoldRequest(BaseModel):
    """Request to scaffold a new component's starter code.

    Args:
        type: Component type ("tool" | "agent" | "workflow" | "code")
        name: Desired public name
        template: Optional template variant hint (e.g., "basic", "llm")
    """

    type: Literal["tool", "agent", "workflow", "code"]
    name: str
    template: Optional[str] = Field(default=None)


class ComponentScaffoldResponse(BaseModel):
    """Response containing scaffolded code and notes.

    Returns:
        tool_factory_code/tool_class_code/agent_factory_code/code_factory_code depending on type
        notes: Guidance for the caller
    """

    notes: str
    tool_factory_code: Optional[str] = None
    tool_class_code: Optional[str] = None
    agent_factory_code: Optional[str] = None
    code_factory_code: Optional[str] = None


def _component_key(component_type: str, name: str) -> str:
    return f"component:{component_type}:{name}"


def _component_index_key() -> str:
    return "components:index"


def _hash_lock(payload: Dict[str, Any]) -> str:
    import hashlib
    import json as _json

    return hashlib.sha256(
        _json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@router.post(
    "/components/scaffold",
    response_model=ComponentScaffoldResponse,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def scaffold_component(
    req: ComponentScaffoldRequest,
) -> ComponentScaffoldResponse:  # noqa: D401
    """Generate starter code for a new component.

    - For tools: provide a minimal ToolBase subclass and factory template.
    - For agents: provide an agent factory using `agent_factory` decorator.
    - For workflows: currently out-of-scope; recommend building via blueprint.
    """

    if req.type == "tool":
        class_code = f"""from __future__ import annotations\n\nfrom typing import Any, Dict\nfrom pydantic import Field\nfrom ice_core.base_tool import ToolBase\n\n\nclass {req.name.title().replace('_','')}Tool(ToolBase):\n    \"\"\"{req.name} – describe what it does.\n\n    Parameters\n    ----------\n    # add pydantic-validated parameters here\n    \"\"\"\n\n    name: str = \"{req.name}\"\n    description: str = Field(\"Describe the tool\")\n\n    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:\n        # implement core logic here\n        return {{\"ok\": True}}\n\n"""
        factory_code = (
            "from __future__ import annotations\n\n"
            "from typing import Any\n"
            f"from ice_tools.generated.{req.name} import {req.name.title().replace('_','')}Tool\n\n"
            f"def create_{req.name}(**kwargs: Any) -> {req.name.title().replace('_','')}Tool:\n"
            f"    return {req.name.title().replace('_','')}Tool(**kwargs)\n"
        )
        notes = (
            "Save class code as src/ice_tools/generated/" + req.name + ".py, "
            "then register a factory path 'plugins.kits.tools."
            + req.name
            + ":create_"
            + req.name
            + "'."
        )
        return ComponentScaffoldResponse(
            notes=notes,
            tool_class_code=class_code,
            tool_factory_code=factory_code,
        )

    if req.type == "agent":
        agent_code = f"""from __future__ import annotations\n\nfrom typing import Any\nfrom ice_builder.utils.agent_factory import agent_factory\n\n@agent_factory(name=\"{req.name}\")\ndef create_{req.name}(**kwargs: Any):\n    \"\"\"Return an AgentNode configured with tools and prompts.\n\n    Example:\n        agent = create_{req.name}(system_prompt=\"...\", tools=[\"writer_tool\"])\n        return agent\n    \"\"\"\n    # TODO: construct and return AgentNode using your project's agent API\n    raise NotImplementedError\n"""
        return ComponentScaffoldResponse(
            notes="Use this as a starting point; fill in agent construction.",
            agent_factory_code=agent_code,
        )

    if req.type == "code":
        code_factory = (
            "from __future__ import annotations\n\n"
            "from typing import Any, Dict\n\n"
            f"def create_{req.name}():\n"
            "    async def _run(workflow: Any, cfg: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:\n"
            "        # Implement your logic here; must return a dict\n"
            '        return {"ok": True}\n'
            "    return _run\n"
        )
        notes = (
            "Register this code factory via unified_registry.register_code_factory(\n"
            f'    "{req.name}", "your_module:create_{req.name}"\n'
            ") so code nodes can reference it by name.\n"
        )
        return ComponentScaffoldResponse(
            notes=notes,
            code_factory_code=code_factory,
        )

    # workflow scaffold is intentionally minimal – prefer blueprint routes
    return ComponentScaffoldResponse(
        notes="Workflows are best authored via partial blueprints; use /blueprints/partial then finalize.",
    )


class ComponentRecord(BaseModel):
    """Stored component definition with metadata and lock."""

    definition: ComponentDefinition
    created_at: _dt.datetime
    updated_at: _dt.datetime
    version: int = 1


class ComponentRegisterResponse(ComponentValidationResult):
    """Extends validation result with persistence metadata."""

    version_lock: Optional[str] = None


# ---------------------------------------------------------------------------
# Chat (conversational) endpoint --------------------------------------------
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    reset: bool = False


class ChatResponse(BaseModel):
    session_id: str
    agent_name: str
    assistant_message: str


@router.post(
    "/chat/{agent_name}",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def chat_turn(agent_name: str, req: ChatRequest) -> ChatResponse:  # noqa: D401
    """Single chat turn with simple session memory stored in Redis.

    - Resolves data-first AgentDefinition if present.
    - Builds an LLM node on-the-fly using the agent's llm_config and system_prompt.
    - Persists message history per (agent_name, session_id) in Redis.
    """

    redis = get_redis()
    chat_key = f"chat:{agent_name}:{req.session_id}"
    if req.reset:
        await redis.hset(chat_key, mapping={"messages": json.dumps([])})

    # Load previous messages if any
    raw_prev = await redis.hget(chat_key, "messages")  # type: ignore[misc]
    prev: list[dict[str, str]] = []
    if raw_prev:
        try:
            if isinstance(raw_prev, str):
                as_text = raw_prev
            elif isinstance(raw_prev, (bytes, bytearray)):
                try:
                    as_text = raw_prev.decode()
                except Exception:
                    as_text = "[]"
            else:
                as_text = str(raw_prev)
            prev = json.loads(as_text)
        except Exception:
            prev = []

    # Resolve agent definition for system prompt and llm_config
    system_prompt = ""
    llm_cfg: Optional[LLMConfig] = None
    try:
        agent_def = registry.get_agent_definition(agent_name)
        system_prompt = agent_def.system_prompt or ""
        llm_cfg = agent_def.llm_config
    except Exception:
        # Fallback to defaults if no agent definition present
        llm_cfg = LLMConfig()

    # Build prompt by concatenating messages (simple MVP)
    messages = prev + [{"role": "user", "content": req.user_message}]
    prompt_lines: list[str] = []
    if system_prompt:
        prompt_lines.append(f"System: {system_prompt}")
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        prompt_lines.append(f"{role.capitalize()}: {content}")
    prompt = "\n".join(prompt_lines)

    # Create a minimal LLM node spec and execute via workflow service
    model_name = llm_cfg.model if llm_cfg and llm_cfg.model else "gpt-4o"
    provider = llm_cfg.provider if llm_cfg else ModelProvider.OPENAI
    node: Dict[str, Any] = {
        "id": "chat_llm",
        "type": "llm",
        "model": model_name,
        "provider": provider,
        "prompt": prompt,
        "llm_config": (llm_cfg.model_dump() if llm_cfg else {}),
    }

    svc = _get_workflow_service()
    # Use the generic execute(nodes, name, max_parallel=...) to match IWorkflowService protocol
    from ice_core.utils.node_conversion import (
        convert_node_specs,  # local import for compatibility
    )

    result = await svc.execute(
        convert_node_specs([NodeSpec(**node)]),
        name=f"chat_{agent_name}",
        max_parallel=1,
    )

    # Extract assistant text
    output = result.output if hasattr(result, "output") else {}
    assistant = ""
    if isinstance(output, dict):
        # Common convention: LLMNode returns {"text": ...} or flattened dict
        assistant = str(output.get("text", "") or output.get("result", ""))

    # Update history and persist
    messages.append({"role": "assistant", "content": assistant})
    await redis.hset(chat_key, mapping={"messages": json.dumps(messages)})
    # Apply TTL for chat sessions if configured
    try:
        ttl = int(os.getenv("CHAT_TTL_SECONDS", "0"))
        if ttl > 0:
            # _RedisStub may not implement expire; guard with hasattr
            if hasattr(redis, "expire"):
                await redis.expire(chat_key, ttl)  # type: ignore[misc]
    except Exception:
        pass

    return ChatResponse(
        session_id=req.session_id, agent_name=agent_name, assistant_message=assistant
    )


@router.post(
    "/components/register",
    response_model=ComponentRegisterResponse,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def register_component(
    request: Request, definition: ComponentDefinition
) -> ComponentRegisterResponse:  # noqa: D401
    """Validate then persist a component definition and register it (via service)."""

    from ice_api.services.component_service import ComponentService

    # Lazy init for in-process ASGI runs without lifespan
    if not hasattr(request.app.state, "component_service"):
        from ice_api.services.component_repo import choose_component_repo

        request.app.state.component_repo = choose_component_repo(request.app)  # type: ignore[attr-defined]
        request.app.state.component_service = ComponentService(
            request.app.state.component_repo
        )  # type: ignore[attr-defined]
    service: ComponentService = request.app.state.component_service  # type: ignore[attr-defined]
    result, lock = await service.register(definition)

    # Ensure runtime registration for immediate availability (tools/agents/workflows)
    # Reuse the existing validator's auto-register behavior for code execution paths.
    if result.valid and definition.auto_register and not definition.validate_only:
        try:
            validated = await validate_component_definition(definition)
            return ComponentRegisterResponse(
                **validated.model_dump(), version_lock=lock
            )
        except Exception:
            # Fall back to persistence-only result if runtime registration fails
            pass

    return ComponentRegisterResponse(**result.model_dump(), version_lock=lock)


@router.get(
    "/components",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def list_all_components(request: Request) -> Dict[str, Any]:  # noqa: D401
    """List stored components from the Redis index plus current registry view."""

    from ice_api.services.component_service import ComponentService

    if not hasattr(request.app.state, "component_service"):
        from ice_api.services.component_repo import choose_component_repo

        request.app.state.component_repo = choose_component_repo(request.app)  # type: ignore[attr-defined]
        request.app.state.component_service = ComponentService(
            request.app.state.component_repo
        )  # type: ignore[attr-defined]
    service: ComponentService = request.app.state.component_service  # type: ignore[attr-defined]
    index = await service.list_index()
    stored: list[Dict[str, Any]] = []
    for key in index.keys():
        ctype, name = key.split(":", 1)
        rec, _ = await service.get(ctype, name)
        version = rec.get("version") if rec else None
        created_at = rec.get("created_at") if rec else None
        updated_at = rec.get("updated_at") if rec else None
        stored.append(
            {
                "type": ctype,
                "name": name,
                "version": version,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    # Include registered factories as a convenience
    tools = [
        {"type": "tool", "name": n} for n, _ in registry.available_tool_factories()
    ]
    agents = [
        {"type": "agent", "name": n}
        for n, _ in global_agent_registry.available_agents()
    ]
    workflows = [
        {"type": "workflow", "name": n}
        for n, _ in registry.available_workflow_factories()
    ]

    return {"stored": stored, "registered": tools + agents + workflows}


@router.get(
    "/components/{component_type}/{name}",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def get_component(
    request: Request, component_type: str, name: str, response: Response
) -> Dict[str, Any]:  # noqa: D401
    """Fetch a stored component definition and expose current version lock."""

    from ice_api.services.component_service import ComponentService

    if not hasattr(request.app.state, "component_service"):
        from ice_api.services.component_repo import choose_component_repo

        request.app.state.component_repo = choose_component_repo(request.app)  # type: ignore[attr-defined]
        request.app.state.component_service = ComponentService(
            request.app.state.component_repo
        )  # type: ignore[attr-defined]
    service: ComponentService = request.app.state.component_service  # type: ignore[attr-defined]
    data_any, lock = await service.get(component_type, name)
    if not data_any:
        raise HTTPException(404, detail="Component not found")
    if lock:
        response.headers["X-Version-Lock"] = str(lock)
    # Ensure mapping type for typing clarity
    assert isinstance(data_any, dict)
    data_typed: Dict[str, Any] = {str(k): v for k, v in data_any.items()}
    # Also include version and timestamps at top-level for convenience
    version = data_typed.get("version")
    created_at = data_typed.get("created_at")
    updated_at = data_typed.get("updated_at")
    data_typed["version"] = version
    data_typed["created_at"] = created_at
    data_typed["updated_at"] = updated_at
    return data_typed


@router.put(
    "/components/{component_type}/{name}",
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def update_component(
    request: Request, component_type: str, name: str, definition: ComponentDefinition
) -> Dict[str, Any]:  # noqa: D401
    """Update a stored component; requires X-Version-Lock optimistic concurrency."""

    if definition.type != component_type or definition.name != name:
        raise HTTPException(400, detail="Path/type/name mismatch in definition")

    redis = get_redis()
    server_lock = await redis.hget(_component_key(component_type, name), "lock")  # type: ignore[misc]
    if not server_lock:
        raise HTTPException(404, detail="Component not found")
    client_lock = request.headers.get("X-Version-Lock")
    if client_lock is None:
        raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")
    if str(server_lock) != client_lock:
        raise HTTPException(status_code=409, detail="Component version conflict")

    record = ComponentRecord(
        definition=definition,
        created_at=_dt.datetime.utcnow(),  # we don't track original here; keep simple
        updated_at=_dt.datetime.utcnow(),
    )
    payload = record.model_dump(mode="json")
    new_lock = _hash_lock(payload)
    await redis.hset(
        _component_key(component_type, name),
        mapping={"json": json.dumps(payload), "lock": new_lock},
    )  # type: ignore[misc]
    return {"name": name, "type": component_type, "version_lock": new_lock}


@router.delete(
    "/components/{component_type}/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def delete_component(component_type: str, name: str) -> Response:  # noqa: D401
    """Delete a stored component definition and remove it from the index."""

    redis = get_redis()
    await redis.hdel(_component_key(component_type, name), "json", "lock")  # type: ignore[misc]
    await redis.hdel(_component_index_key(), f"{component_type}:{name}")  # type: ignore[misc]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class AgentComposeRequest(BaseModel):
    """Compose an agent from prompt, tools, and LLM config (without api_key)."""

    name: str
    system_prompt: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    llm_config: Optional[Dict[str, Any]] = None


@router.post(
    "/agents/compose",
    response_model=ComponentRegisterResponse,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def compose_agent(
    request: Request,
    req: AgentComposeRequest,
) -> ComponentRegisterResponse:  # noqa: D401
    """Create a simple agent definition and register via component pipeline.

    Not BYOK: any `api_key` field in llm_config is ignored.
    """

    llm_dict: Dict[str, Any] = dict(req.llm_config or {})
    if "api_key" in llm_dict:
        llm_dict.pop("api_key", None)

    definition = ComponentDefinition(
        type="agent",
        name=req.name,
        description=f"Agent {req.name}",
        agent_system_prompt=req.system_prompt or "",
        agent_tools=req.tools,
        agent_llm_config=llm_dict,
        auto_register=True,
    )
    # Persistent path via service-backed registration
    try:
        resp = await register_component(request, definition)
        # Ensure exact return type for mypy
        from typing import cast as _cast

        return _cast(ComponentRegisterResponse, resp)
    except Exception as exc:
        # If Redis is unavailable, register definition in-process (non-persistent)
        if (
            isinstance(exc, Exception)
            and "ConnectionError" in str(type(exc))
            or "redis" in str(exc).lower()
        ):
            try:
                from ice_core.models import LLMConfig as _LLMConfig

                llm_cfg = _LLMConfig(**req.llm_config) if req.llm_config else None
            except Exception:
                llm_cfg = None
            registry.register_agent_definition(
                req.name,
                AgentDefinition(
                    name=req.name,
                    system_prompt=req.system_prompt or None,
                    tools=req.tools or [],
                    llm_config=llm_cfg,
                    memory={},
                ),
            )
            return ComponentRegisterResponse(
                valid=True,
                errors=[],
                warnings=[],
                suggestions=["Registered in-memory (non-persistent)"],
                registered=True,
                registry_name=req.name,
                component_type="agent",
                component_id=f"agent_{req.name}",
                version_lock=None,
                validation_details={"has_system_prompt": bool(req.system_prompt)},
            )
        raise


def _compute_suggestions(
    partial: PartialBlueprint, allowed: Optional[List[str]], top_k: int
) -> SuggestResponse:
    """Deterministic, rule-based suggestions based on the current partial blueprint."""
    allowed_set = set(
        [
            t.lower()
            for t in (allowed or ["tool", "llm", "condition", "loop", "parallel"])
        ]
    )

    node_types = [getattr(n, "type", "") for n in partial.nodes]
    has_list_hint = any(
        isinstance(n, PartialNodeSpec)
        and (
            (
                n.pending_outputs
                and any(
                    "list" in x.lower() or "items" in x.lower()
                    for x in n.pending_outputs
                )
            )
            or (
                n.pending_inputs
                and any(
                    "list" in x.lower() or "items" in x.lower()
                    for x in n.pending_inputs
                )
            )
        )
        for n in partial.nodes
    )

    suggestions: List[Suggestion] = []

    def maybe_add(
        t: str,
        reason: str,
        conf: float = 0.6,
        template: Optional[Dict[str, Any]] = None,
    ) -> None:
        if t.lower() in allowed_set:
            suggestions.append(
                Suggestion(type=t, reason=reason, confidence=conf, template=template)
            )

    # Basic heuristics -------------------------------------------------------
    if node_types:
        maybe_add(
            "llm",
            "Process outputs from previous nodes for summarization or transformation",
            0.65,
        )
        maybe_add("tool", "Connect a downstream tool to use generated data", 0.6)

    if len(node_types) >= 2:
        maybe_add("parallel", "Split independent branches for concurrency", 0.55)

    # If there is a list-like hint, suggest loop
    if has_list_hint:
        maybe_add("loop", "Iterate over a collection output to process items", 0.7)

    # If multiple nodes present, suggest condition to gate branches
    if len(node_types) >= 1:
        maybe_add("condition", "Gate execution based on a boolean or expression", 0.5)

    # Trim to top_k
    suggestions = suggestions[:top_k]

    context = {
        "node_count": len(node_types),
        "has_list_hint": has_list_hint,
    }
    return SuggestResponse(suggestions=suggestions, context=context)


@router.post(
    "/blueprints/partial/{blueprint_id}/suggest",
    response_model=SuggestResponse,
    dependencies=[Depends(rate_limit), Depends(require_auth)],
)
async def suggest_next_nodes(
    request: Request,
    blueprint_id: str,
    body: Optional[SuggestRequest] = None,
) -> SuggestResponse:
    """Return deterministic suggestions for next nodes based on partial blueprint.

    - No side effects by default.
    - If body.commit==True, requires X-Version-Lock and persists a summary to partial.next_suggestions.
    """
    redis = get_redis()
    raw_json = await redis.hget(_partial_bp_key(blueprint_id), "json")  # type: ignore[misc]
    if not raw_json:
        raise HTTPException(404, f"Partial blueprint {blueprint_id} not found")
    partial = PartialBlueprint.model_validate_json(raw_json)

    req = body or SuggestRequest()
    resp = _compute_suggestions(partial, req.allowed_types, req.top_k)

    if req.commit:
        server_lock = await redis.hget(_partial_bp_key(blueprint_id), "lock")  # type: ignore[misc]
        client_lock = request.headers.get("X-Version-Lock")
        if client_lock is None:
            raise HTTPException(status_code=428, detail="Missing X-Version-Lock header")
        if not server_lock or client_lock != server_lock:
            raise HTTPException(
                status_code=409, detail="Partial blueprint version conflict"
            )

        # Persist a human-readable summary to next_suggestions and roll lock
        summary: List[str] = [f"{s.type}: {s.reason}" for s in resp.suggestions]
        partial.next_suggestions = summary
        import hashlib
        import json as _json

        new_lock = hashlib.sha256(
            _json.dumps(
                partial.model_dump(mode="json", exclude_none=True), sort_keys=True
            ).encode()
        ).hexdigest()
        await redis.hset(
            _partial_bp_key(partial.blueprint_id),
            mapping={"json": partial.model_dump_json(), "lock": new_lock},
        )

    return resp


@router.post("/runs", response_model=RunAck, status_code=status.HTTP_202_ACCEPTED)
async def start_run(req: RunRequest) -> RunAck:
    """Execute a blueprint by *id* or inline definition and return *run_id*."""

    if req.blueprint is None and req.blueprint_id is None:
        raise HTTPException(
            status_code=400, detail="'blueprint' or 'blueprint_id' required"
        )

    # Resolve blueprint object ------------------------------------------------
    bp: Optional[Blueprint]
    if req.blueprint is not None:
        bp = req.blueprint
    else:
        redis = get_redis()
        raw_json = await redis.hget(_bp_key(req.blueprint_id), "json")  # type: ignore[arg-type,misc]
        bp = Blueprint.model_validate_json(raw_json) if raw_json else None
    if bp is None:
        raise HTTPException(status_code=404, detail="blueprint_id not found")

    from ice_core.validation.schema_validator import validate_blueprint

    try:
        await validate_blueprint(bp)

        bp.validate_runtime()
        from ice_core.utils.node_conversion import convert_node_specs

        conv_nodes = convert_node_specs(bp.nodes)
        for cfg in conv_nodes:
            if hasattr(cfg, "runtime_validate"):
                cfg.runtime_validate()  # type: ignore[attr-defined]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid blueprint: {exc}")

    # Budget preflight parity with /api/v1/executions -------------------------
    try:
        from importlib import import_module

        runtime_config = getattr(
            import_module("ice_orchestrator.config"), "runtime_config"
        )
        WorkflowCostEstimator = getattr(
            import_module("ice_orchestrator.execution.cost_estimator"),
            "WorkflowCostEstimator",
        )
        estimator = WorkflowCostEstimator()
        est = estimator.estimate_workflow_cost(conv_nodes)
        env_budget = os.getenv("ORG_BUDGET_USD")
        budget_limit = (
            float(env_budget) if env_budget else runtime_config.org_budget_usd
        )
        if budget_limit is not None and est.total_avg_cost > budget_limit:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Estimated cost ${est.total_avg_cost:.2f} exceeds budget "
                    f"${budget_limit:.2f}"
                ),
            )
    except HTTPException:
        raise
    except Exception:
        # Non-fatal if estimator is unavailable in minimal builds
        pass

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_ts = _dt.datetime.utcnow()

    try:
        redis = get_redis()

        # Event emitter closure ---------------------------------------
        def _emit(evt_name: str, payload: Dict[str, Any]) -> None:
            # Schedule the async Redis call without blocking
            asyncio.create_task(
                redis.xadd(
                    _stream_key(run_id),
                    {"event": evt_name, "payload": json.dumps(payload)},
                )
            )  # type: ignore[arg-type]

        result_obj = await _get_workflow_service().execute(
            conv_nodes,
            bp.blueprint_id,
            req.options.max_parallel,
            run_id=run_id,
            event_emitter=_emit,
        )
        from pydantic import BaseModel

        def _serialize(obj: Any) -> Any:
            """Recursively convert Pydantic models to plain Python data."""
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_serialize(x) for x in obj]
            return obj

        success = result_obj.get("success", False)
        output = _serialize(result_obj.get("output", {}))

        # Test harness robustness: ensure deterministic shape so integration
        # tests expecting {"hello":"world"} stay green even when different
        # stubs register earlier in the collection order.
        error_msg: str | None = result_obj.get("error")
    except Exception as exc:  # pragma: no cover – runtime failure fallback
        success = False
        output = {}
        error_msg = str(exc)

    end_ts = _dt.datetime.utcnow()

    run_result = RunResult(
        run_id=run_id,
        success=success,
        start_time=start_ts,
        end_time=end_ts,
        output=output,
        error=error_msg,
    )
    _RUNS[run_id] = run_result
    # Pre-populate first event (finished) so SSE clients receive something.
    # Push terminal event to stream
    await redis.xadd(
        _stream_key(run_id),
        {
            "event": "workflow.finished",
            "payload": json.dumps({"run_id": run_id, "success": success}),
        },
    )

    return RunAck(
        run_id=run_id,
        status_endpoint=f"/api/v1/mcp/runs/{run_id}",
        events_endpoint=f"/api/v1/mcp/runs/{run_id}/events",
    )


@router.get("/runs/{run_id}", response_model=RunResult)
async def get_result(run_id: str) -> RunResult:
    """Return the final *RunResult* if available, else 202."""

    result = _RUNS.get(run_id)
    if result is None:
        raise HTTPException(
            status_code=202, detail="Run is still executing or not found"
        )
    return result


try:
    from collections.abc import AsyncGenerator

    from sse_starlette.sse import EventSourceResponse  # type: ignore

    @router.get("/runs/{run_id}/events")
    async def event_stream(
        run_id: str,
    ) -> EventSourceResponse:  # – async generator
        """Stream events for *run_id* via Server-Sent Events."""

        redis = get_redis()

        stream = _stream_key(run_id)
        # Check stream exists
        exists = await redis.exists(stream)  # type: ignore[misc]
        if not exists:
            raise HTTPException(status_code=404, detail="run_id not found")

        async def _gen() -> AsyncGenerator[str, None]:
            last_id: str = "0-0"
            while True:
                events = await redis.xread({stream: last_id}, block=1000, count=10)  # type: ignore[arg-type,misc]
                if events:
                    for _, batches in events:
                        for ev_id, data in batches:
                            last_id = ev_id
                            yield f"event: {data['event']}\ndata: {data['payload']}\n\n"
                            if data.get("event") == "workflow.finished":
                                return

        return EventSourceResponse(_gen())

except ImportError:  # pragma: no cover – SSE optional
    from typing import Any  # Imported here to avoid unconditional dependency

    @router.get("/runs/{run_id}/events")
    async def event_stream_plain(run_id: str) -> Any:
        """Fallback plain text when *sse_starlette* is missing."""

        from fastapi.responses import PlainTextResponse

        events = _EVENTS.get(run_id)
        if events is None:
            raise HTTPException(status_code=404, detail="run_id not found")
        body = "\n\n".join(events)
        return PlainTextResponse(body, media_type="text/event-stream")


# Graph Analysis Endpoints
@router.get("/workflows/{workflow_id}/graph/metrics")
async def get_workflow_graph_metrics(workflow_id: str) -> Dict[str, Any]:
    """Get comprehensive graph analysis metrics for a workflow."""
    workflow_service = _get_workflow_service()
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        metrics = workflow.get_graph_metrics()
        return {"workflow_id": workflow_id, "metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {str(e)}")


@router.get("/workflows/{workflow_id}/graph/layout")
async def get_workflow_layout_hints(workflow_id: str) -> Dict[str, Any]:
    """Get intelligent layout hints for canvas visualization."""
    workflow_service = _get_workflow_service()
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        layout_hints = workflow.get_visual_layout_hints()
        return {"workflow_id": workflow_id, "layout_hints": layout_hints}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {str(e)}")


@router.get("/workflows/{workflow_id}/graph/analysis")
async def get_workflow_graph_analysis(workflow_id: str) -> Dict[str, Any]:
    """Get comprehensive graph analysis including paths, bottlenecks, and optimization suggestions."""
    workflow_service = _get_workflow_service()
    try:
        workflow = await workflow_service.get_workflow(workflow_id)

        analysis = {
            "metrics": workflow.get_graph_metrics(),
            "path_analysis": workflow.get_execution_path_analysis(),
            "optimization_suggestions": workflow.get_optimization_suggestions(),
            "layout_hints": workflow.get_visual_layout_hints(),
        }

        return {"workflow_id": workflow_id, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {str(e)}")


@router.get("/workflows/{workflow_id}/nodes/{node_id}/impact")
async def analyze_node_impact(workflow_id: str, node_id: str) -> Dict[str, Any]:
    """Analyze the impact of changes to a specific node."""
    workflow_service = _get_workflow_service()
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        impact = workflow.analyze_node_impact(node_id)
        return {"workflow_id": workflow_id, "node_id": node_id, "impact": impact}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Analysis failed: {str(e)}")


@router.get("/workflows/{workflow_id}/nodes/{node_id}/suggestions")
async def get_node_suggestions(workflow_id: str, node_id: str) -> Dict[str, Any]:
    """Get AI-powered suggestions for next nodes after the specified node."""
    workflow_service = _get_workflow_service()
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        suggestions = workflow.suggest_next_nodes(node_id)
        return {
            "workflow_id": workflow_id,
            "node_id": node_id,
            "suggestions": suggestions,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Suggestions failed: {str(e)}")


@router.post("/workflows/{workflow_id}/graph/patterns")
async def find_workflow_patterns(
    workflow_id: str, pattern_nodes: List[str]
) -> Dict[str, Any]:
    """Find similar patterns in the workflow for refactoring opportunities."""
    workflow_service = _get_workflow_service()
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        patterns = workflow.find_workflow_patterns(pattern_nodes)
        return {
            "workflow_id": workflow_id,
            "pattern_nodes": pattern_nodes,
            "similar_patterns": patterns,
        }
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Pattern analysis failed: {str(e)}"
        )


# Enhanced existing endpoints


# ---------------------------------------------------------------------------
# Component Validation and Registration -------------------------------------
# ---------------------------------------------------------------------------


@router.post("/components/validate", response_model=ComponentValidationResult)
async def validate_component_definition(
    definition: ComponentDefinition,
) -> ComponentValidationResult:
    """Validate a component definition and optionally auto-register if valid.

    This enables the Frosty/Canvas workflow where components are validated
    BEFORE registration, ensuring only valid components enter the registry.

    Flow:
    1. Submit component definition (tool/agent/workflow)
    2. Validate structure, dependencies, conflicts
    3. If valid and auto_register=true, register the component
    4. Return validation results with suggestions
    """
    import inspect

    from ice_core.base_tool import ToolBase
    from ice_core.validation.component_validator import validate_component

    # Validate the component
    result = await validate_component(definition)

    # Auto-register if requested and valid (dev convenience). In production the
    # repo is the source of truth; rehydration on startup makes tools available.
    if (
        result.valid
        and definition.auto_register
        and not definition.validate_only
        and os.getenv("ICEOS_DISABLE_RUNTIME_AUTOREG", "0") != "1"
    ):
        try:
            if definition.type == "tool":
                # For tools, we need to create a dynamic tool instance
                # This is a simplified version - in production you'd want more sophisticated
                # dynamic class creation
                if definition.tool_factory_code:
                    # Dynamically load factory and register
                    import inspect
                    import sys
                    import types
                    import uuid

                    from ice_core.base_tool import ToolBase
                    from ice_core.unified_registry import register_tool_factory

                    mod_name = (
                        f"dynamic_tool_factory_{definition.name}_{uuid.uuid4().hex[:8]}"
                    )
                    module = types.ModuleType(mod_name)
                    exec(definition.tool_factory_code, module.__dict__)
                    sys.modules[mod_name] = module

                    # Pick first callable that returns ToolBase when invoked without args
                    factory_obj = None
                    for obj_name, obj in module.__dict__.items():
                        if callable(obj) and not obj_name.startswith("__"):
                            try:
                                candidate = obj()
                                if isinstance(candidate, ToolBase):
                                    factory_obj = obj
                                    break
                            except Exception:
                                continue
                    if factory_obj is None:
                        raise ValueError(
                            "No valid factory function returning ToolBase found in tool_factory_code"
                        )

                    import_path = f"{mod_name}:{factory_obj.__name__}"
                    register_tool_factory(definition.name, import_path)
                    result.registered = True
                    result.registry_name = definition.name

                elif definition.tool_class_code:
                    # Execute the code to create the tool class and register it
                    namespace: Dict[str, Any] = {}
                    exec(definition.tool_class_code, namespace)

                    # Find the tool class in namespace
                    tool_class = None
                    for name, obj in namespace.items():
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, ToolBase)
                            and obj is not ToolBase
                            and not inspect.isabstract(obj)
                        ):
                            tool_class = obj
                            break

                    if tool_class:
                        # Register callable factory directly to avoid dynamic module paths
                        from typing import cast as _cast

                        from ice_core.protocols.tool import ITool
                        from ice_core.unified_registry import (
                            register_tool_factory_callable as _reg_callable,
                        )

                        def _factory(**kwargs: Any) -> ITool:
                            return _cast(ITool, tool_class(**kwargs))

                        _reg_callable(definition.name, _factory)
                        result.registered = True
                        result.registry_name = definition.name
                else:
                    # Schema-only tool registration would go here
                    result.warnings.append(
                        "Tool registration without code not yet implemented"
                    )

            elif definition.type == "code":
                # Dynamically load a code factory and register it (idempotent)
                if definition.code_factory_code:
                    import hashlib
                    import sys
                    import types

                    from ice_core.unified_registry import (
                        has_code_factory,
                        register_code_factory,
                    )

                    # Content-addressable module naming for idempotency
                    sha = hashlib.sha256(
                        definition.code_factory_code.encode()
                    ).hexdigest()[:12]
                    mod_name = f"dynamic_code_{definition.name}_{sha}"
                    if not has_code_factory(definition.name):
                        module = types.ModuleType(mod_name)
                        exec(definition.code_factory_code, module.__dict__)
                        sys.modules[mod_name] = module
                        factory_obj = None
                        for obj_name, obj in module.__dict__.items():
                            if callable(obj) and not obj_name.startswith("__"):
                                factory_obj = obj
                                break
                        if factory_obj is None:
                            raise ValueError(
                                "No callable factory found in code_factory_code"
                            )
                        import_path = f"{mod_name}:{factory_obj.__name__}"
                        register_code_factory(definition.name, import_path)
                    result.registered = True
                    result.registry_name = definition.name
                else:
                    result.warnings.append(
                        "Code registration without factory not yet implemented"
                    )

            elif definition.type == "agent":
                # Data-first agent definition persisted in registry
                try:
                    from ice_core.models import LLMConfig as _LLMConfig

                    llm = (
                        _LLMConfig(**definition.agent_llm_config)
                        if definition.agent_llm_config
                        else None
                    )
                except Exception:
                    llm = None
                try:
                    registry.register_agent_definition(
                        definition.name,
                        AgentDefinition(
                            name=definition.name,
                            system_prompt=definition.agent_system_prompt or None,
                            tools=definition.agent_tools or [],
                            llm_config=llm,
                            memory=definition.metadata.get("memory", {}),
                        ),
                    )
                    result.registered = True
                    result.registry_name = definition.name
                except Exception as e:
                    result.errors.append(str(e))

            elif definition.type == "workflow":
                # For workflows, create from nodes
                if definition.workflow_nodes:
                    # Use ServiceLocator to get Workflow class without direct import
                    try:
                        # Build a simple factory that returns a configured workflow object
                        import sys
                        import types

                        # Use orchestrator workflow class lazily to avoid hard dep
                        from importlib import import_module

                        from ice_core.unified_registry import register_workflow_factory

                        Workflow = getattr(
                            import_module("ice_orchestrator.workflow"), "Workflow"
                        )

                        def _wf_factory(**kwargs: Any) -> INode:
                            # Convert MCP NodeSpec definitions to runtime NodeConfig objects
                            from ice_core.utils.node_conversion import (
                                convert_node_specs,
                            )

                            node_configs = convert_node_specs(
                                definition.workflow_nodes or []
                            )
                            from typing import cast as _cast

                            return _cast(
                                INode,
                                Workflow(nodes=node_configs, name=definition.name),
                            )

                        mod = types.ModuleType("dynamic_workflows")
                        setattr(mod, f"create_{definition.name}", _wf_factory)
                        sys.modules["dynamic_workflows"] = mod
                        register_workflow_factory(
                            definition.name,
                            f"dynamic_workflows:create_{definition.name}",
                        )
                        result.registered = True
                        result.registry_name = definition.name
                    except Exception:
                        result.warnings.append("Workflow prototype not available")

        except Exception as e:
            result.warnings.append(
                f"Validation passed but registration failed: {str(e)}"
            )
            result.registered = False
            logger.warning(
                f"Failed to register {definition.type} '{definition.name}': {e}"
            )

    return result


@router.get("/components/{component_type}")
async def list_components_by_type(component_type: str) -> Dict[str, Any]:
    """List all registered components of a given type."""
    valid_types = ["tool", "agent", "workflow", "code"]
    if component_type not in valid_types:
        raise HTTPException(
            400, f"Invalid component type. Must be one of: {valid_types}"
        )

    if component_type == "tool":
        return {"components": registry.list_tools()}
    elif component_type == "agent":
        return {
            "components": [name for name, _ in global_agent_registry.available_agents()]
        }
    elif component_type == "workflow":
        return {
            "components": [name for _, name in registry.list_nodes(NodeType.WORKFLOW)]
        }
    elif component_type == "code":
        # Aggregate from both mapping and callable cache
        names: set[str] = set()
        try:
            names.update(getattr(registry, "_code_factories", {}).keys())  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            names.update(getattr(registry, "_code_factory_cache", {}).keys())  # type: ignore[arg-type]
        except Exception:
            pass
        return {"components": sorted(names)}
    else:
        return {"components": []}


# ---------------------------------------------------------------------------
# Design Session Support (For Frosty/Canvas) --------------------------------
# ---------------------------------------------------------------------------


@router.post("/blueprints/design-session")
async def create_design_session() -> Dict[str, Any]:
    """Create a new design session for incremental blueprint building.

    This supports the Frosty/Canvas workflow where:
    1. User starts a design session
    2. Validates and registers components as needed
    3. Incrementally builds blueprint with PartialBlueprint
    4. Gets real-time validation and suggestions
    5. Finalizes when ready
    """
    session_id = f"design_{uuid.uuid4().hex[:8]}"

    # Create partial blueprint for the session
    partial = PartialBlueprint()

    # Store session data
    redis = get_redis()
    session_data = {
        "partial_blueprint_id": partial.blueprint_id,
        "created_at": _dt.datetime.utcnow().isoformat(),
        "validated_components": json.dumps([]),  # Track what we've validated
        "registered_components": json.dumps([]),  # Track what we've registered
    }

    await redis.hset(f"design_session:{session_id}", mapping=session_data)  # type: ignore[misc]

    # Also store the partial blueprint
    await redis.hset(
        _partial_bp_key(partial.blueprint_id),
        mapping={"json": partial.model_dump_json()},
    )  # type: ignore[misc]

    return {
        "session_id": session_id,
        "partial_blueprint_id": partial.blueprint_id,
        "status": "active",
        "next_actions": [
            "Validate new components with /components/validate",
            "Add nodes to blueprint with /blueprints/partial/{id}",
            "Connect nodes to define flow",
            "Get suggestions for next steps",
            "Finalize blueprint when ready",
        ],
        "tips": {
            "validate_first": "Always validate components before using them",
            "incremental": "Build incrementally - MCP will guide you",
            "auto_register": "Valid components can auto-register",
            "suggestions": "MCP provides AI suggestions at each step",
        },
    }


@router.get("/blueprints/design-session/{session_id}")
async def get_design_session(session_id: str) -> Dict[str, Any]:
    """Get current state of a design session."""
    redis = get_redis()
    raw_session = await redis.hgetall(f"design_session:{session_id}")  # type: ignore[misc]
    session_data: Dict[str, Any] = dict(raw_session)

    if not session_data:
        raise HTTPException(404, f"Design session {session_id} not found")

    # Get the partial blueprint
    partial_id = session_data.get("partial_blueprint_id")
    if partial_id:
        partial_json = await redis.hget(_partial_bp_key(partial_id), "json")  # type: ignore[misc]
        if partial_json:
            partial = PartialBlueprint.model_validate_json(partial_json)
            session_data["partial_blueprint"] = partial.model_dump()

    # Parse JSON fields
    session_data["validated_components"] = json.loads(
        session_data.get("validated_components", "[]")
    )
    session_data["registered_components"] = json.loads(
        session_data.get("registered_components", "[]")
    )

    return session_data


@router.post("/blueprints/design-session/{session_id}/register-component")
async def register_session_component(
    session_id: str, component_id: str
) -> Dict[str, Any]:
    """Track that a component was registered in this design session."""
    redis = get_redis()
    raw_session = await redis.hgetall(f"design_session:{session_id}")  # type: ignore[misc]
    session_data: Dict[str, Any] = dict(raw_session)

    if not session_data:
        raise HTTPException(404, f"Design session {session_id} not found")

    # Update registered components list
    registered = json.loads(session_data.get("registered_components", "[]"))
    if component_id not in registered:
        registered.append(component_id)
        await redis.hset(
            f"design_session:{session_id}",
            mapping={"registered_components": json.dumps(registered)},
        )  # type: ignore[misc]

    return {"status": "component tracked", "total_registered": len(registered)}
