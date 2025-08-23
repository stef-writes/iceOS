"""Executor for agent nodes."""

from datetime import datetime
from typing import Any, Dict

from ice_core.models import AgentNodeConfig, NodeExecutionResult
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_orchestrator.services.agent_runtime import AgentRuntime

__all__ = ["agent_node_executor"]


@register_node("agent")
async def agent_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: AgentNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    """Execute an Agent node.

    Behaviour is identical to the original implementation but now self-contained
    in the dedicated executor module.
    """
    start_time = datetime.utcnow()

    try:
        # Prefer data-first agent definition; fallback to import-based instance
        agent: Any
        try:
            agent_def = registry.get_agent_definition(cfg.package)

            # LLM-backed runtime agent that satisfies IAgent
            import json as _json

            from ice_core.llm.service import LLMService
            from ice_core.models.enums import ModelProvider
            from ice_core.models.llm import LLMConfig

            class _LLMAgent:
                def __init__(
                    self,
                    tools: list[str],
                    system_prompt: str | None,
                    llm_cfg: LLMConfig | None,
                ) -> None:
                    self._allowed = list(tools)
                    self._system_prompt = system_prompt or "You are a helpful agent."
                    # Default to OpenAI gpt-4o if not provided
                    self._llm_cfg = llm_cfg or LLMConfig(
                        provider=ModelProvider.OPENAI, model="gpt-4o"
                    )
                    # Prefer a registry-provided LLM helper (e.g., echo) when present
                    try:
                        self._llm_helper = registry.get_llm_instance(
                            getattr(self._llm_cfg, "model", "gpt-4o")
                        )
                    except Exception:
                        self._llm_helper = None
                    self._llm = LLMService()

                def allowed_tools(self) -> list[str]:
                    return list(self._allowed)

                async def think(self, context: dict[str, Any]) -> str:  # type: ignore[override]
                    prompt = self._render_prompt(context, mode="think")
                    if self._llm_helper is not None:
                        text, _usage, err = await self._llm_helper.generate(
                            llm_config=self._llm_cfg, prompt=prompt, context=context
                        )
                    else:
                        text, _usage, err = await self._llm.generate(
                            self._llm_cfg, prompt
                        )
                    return text or (err or "")

                def _render_prompt(
                    self, context: dict[str, Any], mode: str = "decide"
                ) -> str:
                    # Compact context for the model: include last tool and result snippet
                    agent_ctx = (
                        context.get("agent", {}) if isinstance(context, dict) else {}
                    )
                    last_tool = (
                        agent_ctx.get("last_tool")
                        if isinstance(agent_ctx, dict)
                        else None
                    )
                    last_result = (
                        agent_ctx.get("last_result")
                        if isinstance(agent_ctx, dict)
                        else None
                    )
                    try:
                        last_result_json = (
                            _json.dumps(last_result)[:800]
                            if last_result is not None
                            else "{}"
                        )
                    except Exception:
                        last_result_json = "{}"
                    tools_json = _json.dumps(self._allowed)
                    if mode == "think":
                        return (
                            f"{self._system_prompt}\n\n"
                            f"Context: last_tool={last_tool}\nlast_result={last_result_json}\n"
                            f"Allowed tools: {tools_json}\n"
                            "Briefly state your next step."
                        )
                    # decide mode: instruct JSON action
                    return (
                        f"{self._system_prompt}\n\n"
                        "You must return a strictly valid JSON object with keys: "
                        "tool (string or null), inputs (object), done (boolean), message (string).\n"
                        f"Allowed tools (choose only from this list): {tools_json}\n"
                        f"Context: last_tool={last_tool}\nlast_result={last_result_json}\n"
                        "If a tool is needed, set done=false and choose a tool with minimal inputs from context.\n"
                        "If no further action is needed, set tool=null and done=true.\n"
                        "JSON:"
                    )

                async def decide(self, context: dict[str, Any]) -> dict[str, Any]:  # type: ignore[override]
                    import json as _json

                    # Include concrete guidance for common tools
                    guidance = (
                        "If 'writer_tool' is allowed, prefer it and set inputs to "
                        "{'notes': last_result.get('summary') or last_result or '' , 'style':'concise'} when appropriate."
                    )
                    prompt = (
                        self._render_prompt(context, mode="decide") + "\n" + guidance
                    )
                    if self._llm_helper is not None:
                        text, _usage, _err = await self._llm_helper.generate(
                            llm_config=self._llm_cfg, prompt=prompt, context=context
                        )
                    else:
                        text, _usage, _err = await self._llm.generate(
                            self._llm_cfg, prompt
                        )
                    parsed: dict[str, Any]
                    try:
                        maybe_obj = _json.loads(text) if text else {}
                        parsed = maybe_obj if isinstance(maybe_obj, dict) else {}
                    except Exception:
                        parsed = {}
                    if not parsed:
                        action: dict[str, Any] = {
                            "tool": None,
                            "inputs": {},
                            "done": True,
                            "message": text or "",
                        }
                    else:
                        action = parsed
                    # Normalize and enforce allowed list
                    tool = action.get("tool")
                    if tool is not None:
                        tool = str(tool)
                        if self._allowed and tool not in self._allowed:
                            action["tool"] = None
                            action["done"] = True
                    if "inputs" not in action or not isinstance(
                        action.get("inputs"), dict
                    ):
                        action["inputs"] = {}
                    if "done" not in action:
                        action["done"] = bool(action.get("tool") is None)
                    if "message" not in action:
                        action["message"] = ""
                    return action

            agent = _LLMAgent(
                tools=list(agent_def.tools or []),
                system_prompt=agent_def.system_prompt or None,
                llm_cfg=agent_def.llm_config,
            )
        except Exception:
            # Code-first agent path (importable factory). Pass config hints.
            tool_names: list[str] = []
            try:
                tool_names = [t.name for t in (cfg.tools or [])]  # type: ignore[attr-defined]
            except Exception:
                tool_names = []
            agent = registry.get_agent_instance(
                cfg.package,
                agent_config=(cfg.agent_config or {}),
                llm_config=getattr(cfg, "llm_config", None),
                tools=tool_names,
            )

        # ------------------------------------------------------------------
        # 2. Execute agent – trusted code has full DAG context --------------
        # ------------------------------------------------------------------
        runtime = AgentRuntime()
        agent_output: Any = await runtime.run(
            agent, context=ctx, max_iterations=cfg.max_iterations
        )

        if not isinstance(agent_output, dict):
            agent_output = {"result": agent_output}

        agent_output["agent_package"] = cfg.package
        agent_output["agent_executed"] = True

        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=True,
            output=agent_output,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.package,
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Agent execution: {cfg.package}",
            ),
        )

    except Exception as exc:  # pragma: no cover
        end_time = datetime.utcnow()
        return NodeExecutionResult(
            success=False,
            error=str(exc),
            output={},
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=cfg.package,
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"Agent execution failed: {cfg.package}",
            ),
        )
