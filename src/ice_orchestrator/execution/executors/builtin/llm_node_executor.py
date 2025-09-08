"""Executor for *llm* (LLM node). Canonical implementation."""

from datetime import datetime
from typing import Any, Dict

import ice_core.llm.service as _llm_service_mod
from ice_core.models import LLMNodeConfig, NodeExecutionResult, UsageMetadata
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.protocols.workflow import WorkflowLike  # noqa: F401
from ice_core.unified_registry import register_node, registry
from ice_orchestrator.execution.executors.builtin.helpers import resolve_jinja_templates

__all__ = ["llm_node_executor"]


@register_node("llm")
async def llm_node_executor(
    workflow: "WorkflowLike",  # type: ignore[name-defined]
    cfg: LLMNodeConfig,
    ctx: Dict[str, Any],
) -> NodeExecutionResult:  # noqa: D401, ANN401
    start_time = datetime.utcnow()

    try:
        # Render prompt with Jinja only (single templating path). Missing variables raise.
        try:
            # Unwrap any NodeExecutionResult-like values in ctx to their .output for rendering
            from ice_core.models import (
                NodeExecutionResult as _NER,  # local import to avoid cycles
            )

            ctx_clean: Dict[str, Any] = {
                k: (v.output if isinstance(v, _NER) and v.output is not None else v)
                for k, v in ctx.items()
            }
            jinja_rendered = (
                resolve_jinja_templates(cfg.prompt or "", ctx_clean)
                if cfg.prompt
                else ""
            )
            prompt = (
                jinja_rendered
                if isinstance(jinja_rendered, str)
                else str(jinja_rendered)
            )
        except Exception as exc:
            raise ValueError(f"Failed to render prompt: {exc}") from exc

        # Ensure output schema exists (quiet the runtime warning by setting default)
        try:
            # runtime_validate will itself set a default, but tests warn on missing
            # prior to validation in some call paths. Set a safe default early.

            out_schema = getattr(cfg, "output_schema", None)
            if isinstance(out_schema, dict) and len(out_schema) == 0:
                cfg.output_schema = {"text": "string"}
        except Exception:
            # Non-fatal; continue with execution
            pass

        # Prefer provider/model/params from nested llm_config; fall back to top-level for BC
        # Render Jinja in model fields to support blueprints using expressions like
        # "{{ inputs.model or 'gpt-4o' }}".
        provider: ModelProvider | str = (
            cfg.llm_config.provider
            if cfg.llm_config and getattr(cfg.llm_config, "provider", None)
            else (
                cfg.provider if getattr(cfg, "provider", None) else ModelProvider.OPENAI
            )
        )
        if isinstance(provider, str):
            try:
                provider = ModelProvider(provider)
            except ValueError:
                provider = ModelProvider.OPENAI

        # Resolve model with Jinja against cleaned context when it's a string
        def _render_model(value: Any) -> str:
            try:
                if isinstance(value, str):
                    rendered = resolve_jinja_templates(value, ctx_clean)
                    return rendered if isinstance(rendered, str) else str(rendered)
            except Exception:
                # Fall back to original if rendering fails; validation will catch later
                return str(value)
            return str(value)

        selected_model: Any = (
            cfg.llm_config.model
            if cfg.llm_config and getattr(cfg.llm_config, "model", None) is not None
            else cfg.model
        )
        resolved_model: str = _render_model(selected_model)

        llm_cfg = LLMConfig(
            provider=provider,
            model=resolved_model,
            max_tokens=(
                cfg.llm_config.max_tokens
                if cfg.llm_config
                and getattr(cfg.llm_config, "max_tokens", None) is not None
                else cfg.max_tokens
            ),
            temperature=(
                cfg.llm_config.temperature
                if cfg.llm_config
                and getattr(cfg.llm_config, "temperature", None) is not None
                else cfg.temperature
            ),
        )

        # Prefer factory-based LLM instance when registered; fall back to LLMService
        text: str
        usage: dict[str, int] | None
        error: str | None

        # If a custom LLM factory is registered under cfg.model (or cfg.llm_name), use it
        chosen_llm_name = getattr(cfg, "llm_name", None) or cfg.model
        try:
            llm_helper = registry.get_llm_instance(chosen_llm_name)
            text, usage, error = await llm_helper.generate(
                llm_config=llm_cfg,
                prompt=prompt,
                context=ctx,
            )
        except KeyError:
            llm_service = _llm_service_mod.LLMService()
            text, usage, error = await llm_service.generate(
                llm_config=llm_cfg,
                prompt=prompt,
                context=ctx,
            )
        end_time = datetime.utcnow()

        if error:
            return NodeExecutionResult(
                success=False,
                error=error,
                output={
                    "prompt": prompt,
                    "model": cfg.model,
                    "usage": usage or {},
                },
                metadata=NodeMetadata(
                    node_id=cfg.id,
                    node_type=cfg.type,
                    name=f"llm_{cfg.model}",
                    version="1.0.0",
                    owner="system",
                    error_type="LLMError",
                    provider=cfg.provider,
                    start_time=start_time,
                    end_time=end_time,
                    duration=(end_time - start_time).total_seconds(),
                    description=f"LLM execution failed: {cfg.model}",
                ),
            )

        # Build usage metadata if available
        usage_meta = None
        if usage:
            try:
                usage_meta = UsageMetadata(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    model=str(cfg.model),
                    node_id=str(cfg.id),
                    provider=provider,
                )
            except Exception:
                usage_meta = None

        # Shape output to align with declared output_schema when present
        out_payload: Dict[str, Any] = {
            "response": text,
            "prompt": prompt,
            "model": cfg.model,
            "usage": usage or {},
        }
        try:
            schema_obj = getattr(cfg, "output_schema", None)
            if isinstance(schema_obj, dict):
                # Common schema expects a single 'text' field; keep 'response' too for BC
                if "text" in schema_obj:
                    out_payload.setdefault("text", text)
        except Exception:
            pass

        return NodeExecutionResult(
            success=True,
            output=out_payload,
            usage=usage_meta,
            metadata=NodeMetadata(
                node_id=cfg.id,
                node_type=cfg.type,
                name=f"llm_{cfg.model}",
                version="1.0.0",
                owner="system",
                provider=cfg.provider,
                error_type=None,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"LLM execution: {cfg.model}",
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
                name=f"llm_{getattr(cfg, 'model', 'unknown')}",
                version="1.0.0",
                owner="system",
                error_type=type(exc).__name__,
                provider=cfg.provider,
                start_time=start_time,
                end_time=end_time,
                duration=(end_time - start_time).total_seconds(),
                description=f"LLM execution failed: {getattr(cfg, 'model', 'unknown')}",
            ),
        )
